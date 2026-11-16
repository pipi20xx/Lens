"""Compose 项目操作：带流式进度的后台任务（启动/停止/拉取/重启）。

设计对齐「容器更新任务」（ContainerOpsMixin._update_tasks）：

- 动作在**后台线程**执行，命令输出**逐行**写进任务表，前端只轮询内存任务，
  不会因为 ``docker compose up`` 跑几分钟而卡住一个 HTTP 请求 / 触发网关超时；
- 任务表里维护 ``stage``（阶段）、``items``（Container/Image/Network 条目状态）
  与 ``lines``（原始输出尾部），前端据此画进度条与逐条进度；
- 支持终止：终止会中断当前 compose CLI 进程。镜像拉取阶段随时可停；
  up/down 阶段中途停止时，已创建/已停止的容器不会被自动回滚；
- 同一项目/同一批量动作做防重，重复点击只会复用已有任务（不会重复执行）。

为什么用 CLI 而不是 docker-py：compose 的 ``up`` 会解析 yaml、建网络、
按 depends_on 排序启动，这些语义只有 compose CLI 有。
"""
import codecs
import json
import os
import queue
import re
import shlex
import signal
import subprocess
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.utils.logger import logger

from .base import DockerServiceBase

# compose 进度输出里的状态词 → (条目状态, 中文文案)
_STATUS_WORDS = {
    "creating": ("creating", "创建中"),
    "created": ("created", "已创建"),
    "starting": ("starting", "启动中"),
    "started": ("started", "已启动"),
    "restarting": ("restarting", "重启中"),
    "restarted": ("restarted", "已重启"),
    "stopping": ("stopping", "停止中"),
    "stopped": ("stopped", "已停止"),
    "removing": ("removing", "移除中"),
    "removed": ("removed", "已移除"),
    "recreating": ("recreating", "重建中"),
    "recreated": ("recreated", "已重建"),
    "pulling": ("pulling", "拉取中"),
    "pulled": ("pulled", "已拉取"),
    "downloading": ("downloading", "下载中"),
    "extracting": ("extracting", "解压中"),
    "waiting": ("waiting", "等待中"),
    "running": ("running", "运行中"),
    "up-to-date": ("up-to-date", "已是最新"),
    "skipped": ("skipped", "已跳过"),
    "error": ("error", "出错"),
}
_TERMINAL_OK = {
    "created", "started", "stopped", "removed", "recreated", "pulled",
    "skipped", "restarted", "running", "up-to-date",
}
_COMPOSE_KINDS = ("Container", "Network", "Volume", "Image", "Pod", "Project")
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

# 状态词 → 任务阶段
_STATUS_STAGE = {
    "pulling": "pulling",
    "downloading": "pulling",
    "extracting": "pulling",
    "waiting": "pulling",
    "pulled": "pulling",
    "skipped": "pulling",
    "creating": "creating",
    "created": "creating",
    "recreating": "creating",
    "recreated": "creating",
    "starting": "starting",
    "started": "starting",
    "restarting": "starting",
    "restarted": "starting",
    "stopping": "stopping",
    "stopped": "stopping",
    "removing": "stopping",
    "removed": "stopping",
}

# 各动作的初始阶段 / 说明
_ACTION_STAGE = {
    "up": ("creating", "启动/更新"),
    "pull": ("pulling", "拉取镜像"),
    "down": ("stopping", "停止"),
    "restart": ("starting", "重启"),
}
_ACTION_TIMEOUT = {"up": 3600, "pull": 3600, "down": 600, "restart": 600}


class ComposeOpsMixin(DockerServiceBase):
    # { task_id: {...} }
    _compose_tasks: Dict[str, Dict[str, Any]] = {}
    # { "host_id:path" / "host_id:__bulk__": task_id }
    _active_compose: Dict[str, str] = {}
    _compose_guard = threading.Lock()
    # { host_id: (ts, ([cli...], supports_progress)) }
    _compose_cli_cache: Dict[str, Tuple[float, Tuple[List[str], bool]]] = {}

    # ----------------------------------------------------------- 任务注册表
    @classmethod
    def _compose_key(cls, host_id: str, path: str) -> str:
        return f"{host_id}:{path}"

    @classmethod
    def _get_compose_task_raw(cls, task_id: str) -> Optional[Dict[str, Any]]:
        return cls._compose_tasks.get(task_id)

    @classmethod
    def get_compose_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """返回可 JSON 序列化的任务副本（剔除 threading.Event）。"""
        task = cls._compose_tasks.get(task_id)
        if task is None:
            return None
        return {k: v for k, v in task.items() if k != "cancel_event"}

    @classmethod
    def get_active_compose_task_id(cls, host_id: str, path: str) -> Optional[str]:
        key = cls._compose_key(host_id, path)
        with cls._compose_guard:
            task_id = cls._active_compose.get(key)
        if task_id:
            task = cls._compose_tasks.get(task_id)
            if task and not task.get("done"):
                return task_id
        return None

    @classmethod
    def register_compose_task(cls, host_id: str, project: str, path: str, action: str,
                              is_bulk: bool = False, total: int = 0) -> Optional[str]:
        """登记 compose 任务；同一 host+path（或同一 host 的批量动作）已有任务时返回 None。"""
        now = time.time()
        for tid in list(cls._compose_tasks.keys()):
            t = cls._compose_tasks[tid]
            if t.get("done") and now - (t.get("finished_at") or now) > 3600:
                del cls._compose_tasks[tid]

        key_path = "__bulk__" if is_bulk else path
        with cls._compose_guard:
            key = cls._compose_key(host_id, key_path)
            existing = cls._active_compose.get(key)
            if existing:
                task = cls._compose_tasks.get(existing)
                if task and not task.get("done"):
                    return None
                cls._active_compose.pop(key, None)

            stage, label = _ACTION_STAGE.get(action, ("pending", action))
            task_id = f"{host_id}_compose_{int(now * 1000)}_{uuid.uuid4().hex[:6]}"
            cls._compose_tasks[task_id] = {
                "task_id": task_id,
                "host_id": host_id,
                "project": project,
                "path": path,
                "action": action,
                "action_label": label,
                "is_bulk": is_bulk,
                "status": "pending",
                "stage": "pending" if not is_bulk else stage,
                "items": {},
                "item_order": [],
                "lines": [],
                "done": False,
                "success": False,
                "error": None,
                "cancel_requested": False,
                "cancel_event": threading.Event(),
                "created_at": now,
                "finished_at": None,
                "progress": {"total": total, "completed": 0, "failed": 0},
            }
            cls._active_compose[key] = task_id
            return task_id

    @classmethod
    def request_cancel_compose_task(cls, task_id: str) -> bool:
        task = cls._compose_tasks.get(task_id)
        if task is None or task.get("done"):
            return False
        task["cancel_requested"] = True
        try:
            task["cancel_event"].set()
        except Exception:
            pass
        return True

    def _invalidate_projects_cache(self) -> None:
        """清掉 compose 项目列表缓存（缓存挂在门面类 DockerService 上）。"""
        cache = getattr(type(self), "_projects_cache", None)
        if isinstance(cache, dict):
            cache.pop(self.host_id, None)

    # --------------------------------------------------------------- 输出解析
    @classmethod
    def _task_item(cls, task: Dict[str, Any], key: str, name: str, kind: Optional[str]) -> Dict[str, Any]:
        item = task["items"].get(key)
        if item is None:
            item = {"name": name, "kind": kind or "", "status": "", "status_text": "", "stage": ""}
            task["items"][key] = item
            task["item_order"].append(key)
        return item

    @classmethod
    def _parse_compose_line(cls, line: str) -> Optional[Tuple[Optional[str], str, str, str]]:
        """从 compose 输出里解析 (资源类型, 名称, 状态词, 额外信息)。

        兼容两种 plain 输出：
          `` Container foo-db-1  Creating ``
          `` Image nginx Pulled ``
          `` foo-db-1  Creating ``
        """
        text = line.strip()
        if not text:
            return None
        text = _ANSI_RE.sub("", text).strip()
        if text.startswith("[+]"):
            text = text[3:].strip()
        words = text.split()
        if len(words) < 2:
            return None

        idx = -1
        for i in range(len(words) - 1, 0, -1):
            if words[i].strip(":.").lower() in _STATUS_WORDS:
                idx = i
                break
        if idx <= 0:
            return None

        head = words[:idx]
        status_word = words[idx].strip(":.").lower()
        extra = " ".join(words[idx + 1:])
        kind = None
        if head and head[0] in _COMPOSE_KINDS:
            kind = head[0]
            head = head[1:]
        if not head:
            return None
        name = " ".join(head)
        return kind, name, status_word, extra

    @classmethod
    def _apply_compose_line(cls, task: Dict[str, Any], raw: str) -> None:
        line = _ANSI_RE.sub("", str(raw)).rstrip()
        if not line.strip():
            return
        task["lines"].append(line)
        if len(task["lines"]) > 200:
            task["lines"] = task["lines"][-200:]

        # 批量任务的条目是"项目"，由 run_compose_bulk 直接维护；
        # 这里只保留输出，不把 [项目名] 前缀行误解析成 Container/Image 条目。
        if task.get("is_bulk"):
            return

        parsed = cls._parse_compose_line(line)
        if not parsed:
            return
        kind, name, status_word, extra = parsed
        status, status_text = _STATUS_WORDS[status_word]
        key = f"{kind}:{name}" if kind else f"?:{name}"
        item = cls._task_item(task, key, name, kind)
        item["status"] = status
        item["status_text"] = status_text + (f" {extra}" if extra else "")
        item["stage"] = _STATUS_STAGE.get(status_word, task.get("stage") or "")

        stage = _STATUS_STAGE.get(status_word)
        if stage and not task.get("is_bulk"):
            task["stage"] = stage
        if status == "error":
            task["progress"]["failed"] = task["progress"].get("failed", 0) + 1

        completed = 0
        for k in task["item_order"]:
            if task["items"][k].get("status") in _TERMINAL_OK:
                completed += 1
        task["progress"]["completed"] = completed
        task["progress"]["total"] = max(task["progress"].get("total", 0), len(task["item_order"]))

    # ------------------------------------------------------------- 命令执行
    def _compose_cli(self) -> Tuple[List[str], bool]:
        """探测 compose CLI 形态：(命令前缀, 是否支持 --progress plain)。按主机缓存 15 分钟。"""
        cached = self._compose_cli_cache.get(self.host_id)
        if cached and time.time() - cached[0] < 900:
            return cached[1]

        result: Tuple[List[str], bool] = (["docker", "compose"], False)
        try:
            res = self.exec_command("docker compose version --short 2>/dev/null", log_error=False, timeout=15)
            ver = (res.get("stdout") or "").strip() if res.get("success") else ""
            m = re.match(r"v?(\d+)", ver)
            if m and int(m.group(1)) >= 2:
                result = (["docker", "compose"], True)
            else:
                res2 = self.exec_command("docker-compose version --short 2>/dev/null", log_error=False, timeout=15)
                if res2.get("success") and (res2.get("stdout") or "").strip():
                    result = (["docker-compose"], False)
        except Exception as e:
            logger.warning(f"[Compose] 探测 compose CLI 失败（保持默认 docker compose）: {e}")
        self._compose_cli_cache[self.host_id] = (time.time(), result)
        return result

    def _build_compose_command(self, path: str, action: str) -> str:
        prefix, supports_progress = self._compose_cli()
        parts = list(prefix)
        if supports_progress:
            parts.append("--progress plain")
        parts.extend(["-f", self._quote_path(path)])
        parts.append("up -d" if action == "up" else action)
        return " ".join(parts)

    def _quote_path(self, path: str) -> str:
        """路径引号：本地主机按当前操作系统选，远程主机一律 POSIX 引号。"""
        if self.host_config.get("type") != "local":
            return shlex.quote(path)
        if os.name == "nt":
            return f'"{path}"' if any(ch in path for ch in " \t") else path
        return shlex.quote(path)

    def _stream_local(self, command: str, cwd: Optional[str], on_line: Optional[Callable[[str], None]],
                      cancel_event: Optional[threading.Event], timeout: int, poll: float) -> Tuple[int, bool, bool]:
        full_cmd = f"cd {self._quote_path(cwd)} && {command}" if cwd else command
        kwargs: Dict[str, Any] = {}
        if os.name != "nt":
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1, **kwargs,
        )
        lines: "queue.Queue[Optional[str]]" = queue.Queue()

        def _reader():
            try:
                if proc.stdout is not None:
                    for line in proc.stdout:
                        lines.put(line)
            except Exception:
                pass
            finally:
                lines.put(None)

        threading.Thread(target=_reader, daemon=True, name=f"compose-out-{proc.pid}").start()

        def _kill():
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
            try:
                proc.wait(timeout=8)
            except Exception:
                try:
                    if os.name != "nt":
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                except Exception:
                    pass

        deadline = time.time() + max(1, timeout)
        while True:
            if cancel_event is not None and cancel_event.is_set():
                _kill()
                return -1, False, True
            remaining = deadline - time.time()
            if remaining <= 0:
                _kill()
                return -1, True, False
            try:
                line = lines.get(timeout=min(poll, remaining))
            except queue.Empty:
                continue
            if line is None:
                break
            if on_line:
                try:
                    on_line(line)
                except Exception:
                    pass
        try:
            code = proc.wait(timeout=10)
        except Exception:
            code = -1
        return code, False, False

    def _stream_ssh(self, command: str, cwd: Optional[str], on_line: Optional[Callable[[str], None]],
                    cancel_event: Optional[threading.Event], timeout: int, poll: float) -> Tuple[int, bool, bool]:
        ssh = self._get_ssh_client()
        if not ssh:
            raise RuntimeError("SSH 连接失败，无法执行 compose 命令")
        full_cmd = f"cd {shlex.quote(cwd)} && {command}" if cwd else command

        transport = ssh.get_transport()
        if transport is None:
            raise RuntimeError("SSH 会话不可用，无法执行 compose 命令")
        chan = transport.open_session()
        chan.settimeout(1.0)
        chan.exec_command(full_cmd)

        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        buf = ""

        def _emit(chunk: str) -> None:
            nonlocal buf
            buf += chunk
            while True:
                m = re.search(r"\r\n|\n|\r", buf)
                if not m:
                    break
                line = buf[:m.start()]
                buf = buf[m.end():]
                if line.strip() and on_line:
                    try:
                        on_line(line)
                    except Exception:
                        pass

        deadline = time.time() + max(1, timeout)
        while True:
            if cancel_event is not None and cancel_event.is_set():
                try:
                    chan.close()
                except Exception:
                    pass
                return -1, False, True
            if time.time() > deadline:
                try:
                    chan.close()
                except Exception:
                    pass
                return -1, True, False

            got = False
            if not transport.is_active():
                # 连接已断开：remote 命令随会话 SIGHUP 结束，交给上层按失败处理
                logger.warning("[Compose] SSH 传输层已断开，中断当前 compose 命令")
                break
            try:
                while chan.recv_ready():
                    data = chan.recv(4096)
                    if not data:
                        break
                    got = True
                    _emit(decoder.decode(data))
                while chan.recv_stderr_ready():
                    data = chan.recv_stderr(4096)
                    if not data:
                        break
                    got = True
                    _emit(decoder.decode(data))
            except Exception as e:
                # 通道超时属于正常（我们本来就 1s 轮询）；真正的异常才记录
                if "timed out" not in str(e).lower():
                    logger.debug(f"[Compose] 读取 SSH 输出中断: {e}")

            if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
                _emit(decoder.decode(b"", True))
                if buf.strip() and on_line:
                    try:
                        on_line(buf)
                    except Exception:
                        pass
                break
            if not got:
                time.sleep(poll)

        try:
            code = chan.recv_exit_status()
        except Exception:
            code = -1
        finally:
            try:
                chan.close()
            except Exception:
                pass
        return code, False, False

    def _stream_shell(self, command: str, cwd: Optional[str] = None,
                      on_line: Optional[Callable[[str], None]] = None,
                      cancel_event: Optional[threading.Event] = None,
                      timeout: int = 1800, poll: float = 0.1) -> Tuple[int, bool, bool]:
        """执行命令并逐行回调输出，返回 (exit_code, timed_out, cancelled)。"""
        if self.host_config.get("type") == "local":
            return self._stream_local(command, cwd, on_line, cancel_event, timeout, poll)
        return self._stream_ssh(command, cwd, on_line, cancel_event, timeout, poll)

    # --------------------------------------------------------------- 结果回检
    def _verify_compose_result(self, path: str, action: str) -> Tuple[bool, str]:
        """命令以非 0 退出时的状态回检（超时/输出被截断时仍能给出可信结论）。"""
        prefix, supports_progress = self._compose_cli()
        cmd = " ".join(list(prefix) + ["-f", self._quote_path(path), "ps", "--format", "json"])
        try:
            res = self.exec_command(cmd, cwd=os.path.dirname(path), log_error=False, timeout=30)
        except Exception:
            return False, ""
        if not res.get("success"):
            return False, ""
        stdout = (res.get("stdout") or "").strip()
        if action == "up":
            states: List[str] = []
            try:
                data = json.loads(stdout) if stdout else []
                rows = data if isinstance(data, list) else [data]
                states = [str(r.get("State") or r.get("Status") or "") for r in rows if isinstance(r, dict)]
            except Exception:
                states = []
            if any(s == "running" for s in states):
                return True, "回检发现项目容器已在运行，判定操作成功"
            return False, ""
        if action == "down":
            if not stdout or stdout in ("[]", "null"):
                return True, "回检发现已无运行容器，判定操作成功"
            return False, ""
        return False, ""

    # --------------------------------------------------------------- 任务执行
    def run_compose_action(self, task_id: str, cancel_event: threading.Event) -> None:
        task = self._compose_tasks.get(task_id)
        if task is None:
            return
        path = task.get("path") or ""
        action = task.get("action") or "up"
        stage, label = _ACTION_STAGE.get(action, ("pending", action))
        task["status"] = "running"
        task["stage"] = stage
        task["lines"].append(f"开始「{label}」· 项目 {task.get('project') or ''}".rstrip())
        logger.info(f"🧩 [Compose] 开始 {action} 项目 {task.get('project')} ({path})")

        try:
            if not path:
                raise RuntimeError("未指定 compose 配置文件路径")
            command = self._build_compose_command(path, action)
            task["lines"].append(f"$ {command}")
            code, timed_out, cancelled = self._stream_shell(
                command,
                cwd=os.path.dirname(path),
                on_line=lambda line: self._apply_compose_line(task, line),
                cancel_event=cancel_event,
                timeout=_ACTION_TIMEOUT.get(action, 1800),
            )

            if cancelled:
                task["status"] = "cancelled"
                task["lines"].append("已终止：compose 命令被中断，已创建/已停止的容器不会自动回滚")
                return
            if timed_out:
                raise RuntimeError(f"执行超时（{_ACTION_TIMEOUT.get(action, 1800)}s），任务已中断，可稍后刷新查看实际状态")
            if code != 0:
                ok, note = self._verify_compose_result(path, action)
                if ok:
                    task["lines"].append(note)
                else:
                    raise RuntimeError(self._tail_error(task) or f"docker compose {action} 执行失败（退出码 {code}）")

            task["success"] = True
            task["status"] = "success"
            task["stage"] = "done"
            task["lines"].append(f"{label}完成")
            logger.info(f"✨ [Compose] 项目 {task.get('project')} {action} 成功")
        except Exception as e:
            task["success"] = False
            task["status"] = "failed"
            task["error"] = str(e)
            task["lines"].append(f"失败: {e}")
            logger.error(f"🚨 [Compose] 项目 {task.get('project')} {action} 失败: {e}")
        finally:
            task["done"] = True
            task["finished_at"] = time.time()
            task["stage"] = "done"
            self._invalidate_projects_cache()
            key = self._compose_key(self.host_id, path)
            with self._compose_guard:
                if self._active_compose.get(key) == task_id:
                    self._active_compose.pop(key, None)

    def run_compose_bulk(self, task_id: str, projects: List[Dict[str, Any]],
                         action: str, cancel_event: threading.Event) -> None:
        """批量动作：逐个项目串行执行，任务表里按项目更新条目状态。"""
        task = self._compose_tasks.get(task_id)
        if task is None:
            return
        stage, label = _ACTION_STAGE.get(action, ("pending", action))
        task["status"] = "running"
        task["stage"] = stage
        total = len(projects)
        task["progress"]["total"] = total

        try:
            for idx, project in enumerate(projects, start=1):
                name = project.get("name") or f"project-{idx}"
                config_file = project.get("config_file") or project.get("path") or ""
                if not config_file:
                    continue
                if not config_file.endswith((".yml", ".yaml")):
                    config_file = os.path.join(config_file, "docker-compose.yml")

                item_key = f"Project:{name}"
                item = self._task_item(task, item_key, name, "Project")
                if cancel_event.is_set():
                    item["status"] = "cancelled"
                    item["status_text"] = "已跳过（批量任务已终止）"
                    continue

                item["status"] = "starting"
                item["status_text"] = "进行中"
                task["lines"].append(f"[{idx}/{total}] {label} {name} …")

                command = self._build_compose_command(config_file, action)
                code, timed_out, cancelled = self._stream_shell(
                    command,
                    cwd=os.path.dirname(config_file),
                    on_line=lambda line, _n=name: self._apply_compose_line(task, f"[{_n}] {line}"),
                    cancel_event=cancel_event,
                    timeout=_ACTION_TIMEOUT.get(action, 1800),
                )

                if cancelled or timed_out:
                    item["status"] = "failed"
                    item["status_text"] = "已终止" if cancelled else "执行超时"
                    task["progress"]["failed"] = task["progress"].get("failed", 0) + 1
                    if cancelled:
                        break
                    continue
                if code != 0:
                    ok, note = self._verify_compose_result(config_file, action)
                    if ok:
                        item["status"] = "done"
                        item["status_text"] = "完成（已回检）"
                        task["lines"].append(f"[{name}] {note}")
                    else:
                        item["status"] = "failed"
                        item["status_text"] = f"失败（退出码 {code}）"
                        task["progress"]["failed"] = task["progress"].get("failed", 0) + 1
                else:
                    item["status"] = "done"
                    item["status_text"] = "完成"
                task["progress"]["completed"] = sum(
                    1 for k in task["item_order"] if task["items"][k].get("status") in ("done", "failed", "cancelled")
                )

            failed = task["progress"].get("failed", 0)
            if cancel_event.is_set():
                task["status"] = "cancelled"
                task["lines"].append("批量任务已终止")
            elif failed:
                task["status"] = "failed"
                task["error"] = f"{failed} 个项目执行失败"
            else:
                task["status"] = "success"
                task["success"] = True
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            task["lines"].append(f"批量任务失败: {e}")
            logger.error(f"🚨 [Compose] 批量 {action} 失败: {e}")
        finally:
            task["done"] = True
            task["finished_at"] = time.time()
            task["stage"] = "done"
            self._invalidate_projects_cache()
            key = self._compose_key(self.host_id, "__bulk__")
            with self._compose_guard:
                if self._active_compose.get(key) == task_id:
                    self._active_compose.pop(key, None)

    @staticmethod
    def _tail_error(task: Dict[str, Any], limit: int = 6) -> str:
        """从输出尾部挑出最可能的错误行，作为失败原因。"""
        tail = [ln for ln in (task.get("lines") or [])[-40:] if ln.strip()]
        interesting = [ln for ln in tail if re.search(r"error|failed|denied|cannot|not found|no such|refused|timeout", ln, re.I)]
        picked = interesting[-limit:] if interesting else tail[-3:]
        return " | ".join(ln.strip() for ln in picked)[:800]
