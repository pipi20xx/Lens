"""Telegram 交互 Bot：long polling 监听消息与回调，提供 Docker 容器管理能力。

所有 Telegram API 调用统一经由 app.services.telegram.client 发出；
所有 Docker 同步调用一律通过 asyncio.to_thread 下放线程池，避免阻塞事件循环。

交互设计：
- 全程原地编辑同一条消息（主机列表 → 容器列表 → 详情 → 操作结果），不刷屏
- 容器列表分页（每页 20 个，按名称排序保证翻页稳定）
- 破坏性操作（停止/重启/更新）需二次确认，并绑定到 Bot 配置的通知会话

callback_data 协议（兼容旧版不带 page 的格式）：
- hl:{host_id}[:{page}]            查看主机容器列表
- hl_back / hosts_back             返回主机列表
- ci:{host_id}:{container_id}[:{page}]  容器详情
- co:{host_id}:{container_id}:{op}[:{page}]  发起容器操作（破坏性操作进入确认页）
- cf:{host_id}:{container_id}:{op}:{page}    确认执行容器操作

轮询 offset 持久化在 data/tg_state.json（按 bot_id）：
- 冷启动且无历史记录时 drop_pending_updates 清积压，避免重放陈旧指令
- 冷启动且有历史记录时恢复 offset，仅处理停机期间的新消息
- 手动重启（保存设置）时 drop_pending_updates=True 丢弃积压
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.core.config_manager import get_config
from app.services.docker_service import DockerService
from app.services.telegram.client import (
    TelegramAPIError,
    close_all_clients,
    get_client,
    sanitize,
)
from app.services.telegram.formatting import b, code, esc
from app.utils.logger import logger

STATE_FILE = "data/tg_state.json"

# 交互命令表（单一来源）：菜单同步与消息路由共用
COMMANDS = [
    ("start", "重新显示欢迎消息"),
    ("status", "查看系统运行概览"),
    ("hosts", "查看 Docker 主机及容器列表"),
]

# 容器操作白名单（防止任意 op 传入 container_action）
CONTAINER_OPS = {"start", "stop", "restart", "remove", "recreate", "update"}

# 破坏性操作：需二次确认，且仅允许在 Bot 配置的通知会话（chat_id）中执行
DESTRUCTIVE_OPS = {"stop", "restart", "remove", "recreate", "update"}

# 容器列表分页大小（Telegram 单条消息 inline 按钮上限为 100）
PAGE_SIZE = 20

# 单个 Bot 并发处理的 update 上限，防止慢命令堆积拖垮后续消息
MAX_CONCURRENT_UPDATES = 3

STATUS_MAP = {
    "running": "运行中 (Running)",
    "exited": "已停止 (Exited)",
    "paused": "已暂停 (Paused)",
    "restarting": "正在重启 (Restarting)",
    "created": "已创建 (Created)",
    "dead": "已损坏 (Dead)",
}

OP_WARNINGS = {
    "stop": "停止后容器内的服务将中断运行。",
    "restart": "重启期间服务会短暂中断。",
    "recreate": "将按原配置重构容器，期间服务会中断。",
    "update": "将拉取最新镜像并重构容器，耗时可能较长，请耐心等待。",
    "remove": "容器将被强制删除，此操作不可恢复！",
}


class TelegramBotWorker:
    _tasks: Dict[str, asyncio.Task] = {}
    _dispatch_tasks: set = set()
    # 运行时状态（供 status 接口读取，不发网络请求）
    _bot_errors: Dict[str, str] = {}
    _bot_usernames: Dict[str, str] = {}

    # ---------- 生命周期 ----------

    @classmethod
    async def start_all(cls, drop_pending: bool = False):
        """启动所有开启了交互功能的 Bot 监听"""
        config = get_config()
        bots = config.get("notification_settings", {}).get("bots", [])
        for bot in bots:
            if bot.get("enabled") and bot.get("is_interactive"):
                await cls.start_bot(bot, drop_pending=drop_pending)

    @classmethod
    async def start_bot(cls, bot_cfg: Dict, drop_pending: bool = False) -> bool:
        """启动单个 Bot 的交互监听，返回是否启动成功。"""
        bot_id = bot_cfg.get("id")
        name = bot_cfg.get("name", bot_id)
        await cls.stop_bot(bot_id)
        cls._bot_errors.pop(bot_id, None)

        client = get_client(bot_cfg.get("token"))
        try:
            # 清理可能残留的 webhook（否则 getUpdates 会永久 409）
            await client.delete_webhook(drop_pending_updates=drop_pending)
            me = await client.get_me()
            cls._bot_usernames[bot_id] = me.get("username") or ""
        except Exception as e:
            err = sanitize(str(e))
            cls._bot_errors[bot_id] = err
            logger.error(f"❌ [TG Bot] Token 校验失败，不启动监听 ({name}): {err}")
            return False

        commands = [{"command": cmd, "description": desc} for cmd, desc in COMMANDS]
        try:
            await client.set_my_commands(commands)
        except Exception as e:
            logger.warning(sanitize(f"⚠️ [TG Bot] 菜单同步失败 ({name}): {e}"))

        task = asyncio.create_task(cls._poll_loop(dict(bot_cfg), drop_pending))
        cls._tasks[bot_id] = task
        logger.info(f"🤖 [TG Bot] 交互监听已启动: {name}")
        return True

    @classmethod
    async def stop_bot(cls, bot_id: str):
        task = cls._tasks.pop(bot_id, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @classmethod
    async def stop_all(cls):
        """优雅关闭：停止所有轮询与待处理 update，释放连接。"""
        for bot_id in list(cls._tasks.keys()):
            await cls.stop_bot(bot_id)
        for task in list(cls._dispatch_tasks):
            task.cancel()
        cls._dispatch_tasks.clear()
        await close_all_clients()
        logger.info("🛑 [TG Bot] 所有交互监听已停止")

    @classmethod
    def get_status(cls, bot_id: str) -> Dict[str, Any]:
        """读取运行时状态。"""
        task = cls._tasks.get(bot_id)
        return {
            "running": bool(task is not None and not task.done()),
            "username": cls._bot_usernames.get(bot_id) or None,
            "error": cls._bot_errors.get(bot_id),
        }

    @classmethod
    async def verify_token(cls, token: str):
        """校验 token 有效性，返回 (ok, username, error)。"""
        try:
            me = await get_client(token).get_me()
            return True, me.get("username"), None
        except Exception as e:
            return False, None, sanitize(str(e))

    # ---------- 轮询 ----------

    @classmethod
    async def _poll_loop(cls, bot_cfg: Dict, drop_pending: bool):
        bot_id = bot_cfg.get("id")
        name = bot_cfg.get("name", bot_id)
        client = get_client(bot_cfg.get("token"))
        poll_timeout = 30

        offset: Optional[int] = None
        drop = drop_pending
        if not drop:
            offset = cls._load_offset(bot_id)
            drop = offset is None  # 无历史记录时清积压，避免重放陈旧指令

        sem = asyncio.Semaphore(MAX_CONCURRENT_UPDATES)
        consecutive_failures = 0
        logger.info(f"🤖 [TG Bot] 交互监听已启动: {name}")

        try:
            while True:
                try:
                    updates = await client.get_updates(
                        offset, poll_timeout=poll_timeout, drop_pending_updates=drop
                    )
                    drop = False
                    consecutive_failures = 0
                except TelegramAPIError as e:
                    if e.status_code in (401, 404):
                        cls._bot_errors[bot_id] = f"Token 无效 (HTTP {e.status_code})"
                        logger.error(f"❌ [TG Bot] Token 无效，停止轮询 ({name}): HTTP {e.status_code}")
                        return
                    if e.status_code == 409:
                        # 轮询冲突（残留 webhook 或旧连接未断），清理后自愈重试
                        logger.warning(f"⚠️ [TG Bot] 轮询冲突 409 ({name})，清理 webhook 后重试...")
                        try:
                            await client.delete_webhook()
                        except Exception:
                            pass
                        await asyncio.sleep(3)
                        continue
                    consecutive_failures += 1
                    delay = min(60, 5 * consecutive_failures)
                    logger.error(sanitize(f"❌ [TG Bot] 轮询失败 ({name}): {e}，{delay}s 后重试"))
                    await asyncio.sleep(delay)
                    continue
                except Exception as e:
                    consecutive_failures += 1
                    delay = min(60, 5 * consecutive_failures)
                    logger.error(sanitize(f"❌ [TG Bot] 轮询异常 ({name}): {e}，{delay}s 后重试"))
                    await asyncio.sleep(delay)
                    continue

                for update in updates or []:
                    offset = update.get("update_id", 0) + 1
                    cls._save_offset(bot_id, offset)
                    cls._dispatch_update(bot_cfg, update, sem)
        except asyncio.CancelledError:
            logger.info(f"🛑 [TG Bot] 交互监听已停止: {name}")
        finally:
            cls._tasks.pop(bot_id, None)

    @classmethod
    def _dispatch_update(cls, bot_cfg: Dict, update: Dict, sem: asyncio.Semaphore):
        """每条 update 独立任务处理，互不阻塞、异常隔离。"""

        async def runner():
            async with sem:
                try:
                    await cls._handle_update(bot_cfg, update)
                except Exception as e:
                    logger.error(sanitize(f"❌ [TG Bot] 处理消息异常 ({bot_cfg.get('name')}): {e}"))

        task = asyncio.create_task(runner())
        cls._dispatch_tasks.add(task)
        task.add_done_callback(cls._dispatch_tasks.discard)

    # ---------- offset 持久化 ----------

    @staticmethod
    def _load_offset(bot_id: str) -> Optional[int]:
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                value = json.load(f).get(bot_id)
            return int(value) if value else None
        except Exception:
            return None

    @staticmethod
    def _save_offset(bot_id: str, offset: int):
        try:
            data = {}
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data[bot_id] = offset
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            tmp = f"{STATE_FILE}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, STATE_FILE)
        except Exception as e:
            logger.warning(f"⚠️ [TG Bot] 保存轮询状态失败: {e}")

    # ---------- 消息处理 ----------

    @classmethod
    async def _handle_update(cls, bot_cfg: Dict, update: Dict):
        if "message" in update:
            msg = update["message"] or {}
            chat_id = str((msg.get("chat") or {}).get("id", ""))
            user_id = str((msg.get("from") or {}).get("id", ""))
            text = (msg.get("text") or "").strip()
            if not chat_id:
                return

            if user_id not in bot_cfg.get("allowed_user_ids", []):
                logger.warning(f"⚠️ [TG Bot] 未授权访问拦截: User={user_id}")
                return

            if not text.startswith("/"):
                return

            # 兼容 /cmd@BotName 后缀与大小写
            cmd = text.split()[0].lstrip("/").split("@", 1)[0].lower()
            if not cmd.isalnum():
                return
            handler = getattr(cls, f"_cmd_{cmd}", None)
            if handler is None:
                return
            await handler(bot_cfg, chat_id)

        elif "callback_query" in update:
            query = update["callback_query"] or {}
            user_id = str((query.get("from") or {}).get("id", ""))
            if user_id not in bot_cfg.get("allowed_user_ids", []):
                await get_client(bot_cfg.get("token")).answer_callback_query(query.get("id"), "⛔ 无权限操作")
                return
            await cls._handle_callback(bot_cfg, query)

    @classmethod
    async def _handle_callback(cls, bot_cfg: Dict, query: Dict):
        data = query.get("data") or ""
        message = query.get("message") or {}
        chat_id = str((message.get("chat") or {}).get("id", ""))
        message_id = message.get("message_id")
        logger.info(f"🖱️ [TG Bot] 收到回调指令: {data}")
        # 先 answer 结束客户端转圈，再执行操作
        await get_client(bot_cfg.get("token")).answer_callback_query(query.get("id"))

        try:
            if data in ("hl_back", "hosts_back"):
                await cls._render_hosts(bot_cfg, chat_id, message_id)
            elif data.startswith("hl:"):
                parts = data.split(":")
                page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                await cls._show_containers(bot_cfg, chat_id, parts[1], page, message_id)
            elif data.startswith("ci:"):
                parts = data.split(":")
                if len(parts) >= 3:
                    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                    await cls._show_container_detail(bot_cfg, chat_id, parts[1], parts[2], page, message_id)
            elif data.startswith("co:"):
                parts = data.split(":")
                if len(parts) >= 4:
                    page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
                    await cls._request_container_op(bot_cfg, chat_id, message_id, parts[1], parts[2], parts[3], page)
            elif data.startswith("cf:"):
                parts = data.split(":")
                if len(parts) == 5:
                    page = int(parts[4]) if parts[4].isdigit() else 0
                    await cls._exec_container_op(bot_cfg, chat_id, message_id, parts[1], parts[2], parts[3], page)
        except Exception as e:
            logger.error(sanitize(f"❌ [TG Bot] 回调处理失败: {e}"))
            await cls._render(bot_cfg, chat_id, message_id, f"❌ 操作执行出错: {esc(e)}")

    # ---------- 命令处理 ----------

    @classmethod
    async def _cmd_start(cls, bot_cfg: Dict, chat_id: str):
        await cls._send_message(
            bot_cfg, chat_id,
            f"👋 你好！我是 {b('Lens 管理助手')}。\n\n"
            "你可以使用以下指令：\n"
            "/hosts - 查看 Docker 主机列表\n"
            "/status - 查看系统概览",
        )

    @classmethod
    async def _cmd_status(cls, bot_cfg: Dict, chat_id: str):
        hosts = get_config().get("docker_hosts", [])
        if not hosts:
            await cls._send_message(bot_cfg, chat_id, "📊 尚未配置任何 Docker 主机。")
            return

        async def probe(host):
            try:
                containers = await cls._list_containers(host)
                running = len([c for c in containers if c.get("status") == "running"])
                return f"🖥 {code(host.get('name'))}\n容器: {running} 运行中 / {len(containers)} 总计"
            except Exception:
                return f"🖥 {code(host.get('name'))}: ❌ 连接失败"

        results = await asyncio.gather(*[probe(h) for h in hosts])
        lines = [f"📊 {b('Docker 系统概览')}", ""]
        lines.extend(results)
        lines.append("")
        lines.append(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await cls._send_message(bot_cfg, chat_id, "\n".join(lines))

    @classmethod
    async def _cmd_hosts(cls, bot_cfg: Dict, chat_id: str):
        await cls._render_hosts(bot_cfg, chat_id, message_id=None)

    # ---------- 渲染辅助 ----------

    @classmethod
    async def _render(cls, bot_cfg: Dict, chat_id: str, message_id: Optional[int], text: str, reply_markup: Optional[Dict] = None):
        """有 message_id 则原地编辑（不刷屏），否则发送新消息。"""
        if message_id:
            await cls._edit_message(bot_cfg, chat_id, message_id, text, reply_markup)
        else:
            await cls._send_message(bot_cfg, chat_id, text, reply_markup)

    @classmethod
    async def _render_hosts(cls, bot_cfg: Dict, chat_id: str, message_id: Optional[int]):
        hosts = get_config().get("docker_hosts", [])
        if not hosts:
            await cls._render(bot_cfg, chat_id, message_id, "尚未配置任何 Docker 主机。")
            return
        buttons = [[{"text": f"🖥 {h.get('name')}", "callback_data": f"hl:{h['id']}"}] for h in hosts]
        await cls._render(bot_cfg, chat_id, message_id, "请选择要管理的主机：", {"inline_keyboard": buttons})

    # ---------- Docker 交互 ----------

    @staticmethod
    def _get_host(host_id: str) -> Optional[Dict]:
        return next(
            (h for h in get_config().get("docker_hosts", []) if h.get("id") == host_id), None
        )

    @staticmethod
    def _is_trusted_chat(bot_cfg: Dict, chat_id: str) -> bool:
        """破坏性操作绑定会话：配置了 chat_id 时仅该会话可执行。"""
        bound = str(bot_cfg.get("chat_id") or "").strip()
        if not bound or bound in ("*", "all"):
            return True
        return bound == str(chat_id).strip()

    @staticmethod
    async def _list_containers(host: Dict):
        """在线程池中实例化服务并拉取容器列表。

        DockerService 构造函数含同步 client.ping() 网络调用，不能放在事件循环里。
        """
        def _load():
            return DockerService(host).list_containers()
        return await asyncio.to_thread(_load)

    @classmethod
    async def _show_containers(cls, bot_cfg: Dict, chat_id: str, host_id: str, page: int = 0, message_id: Optional[int] = None):
        host = cls._get_host(host_id)
        if not host:
            await cls._render(bot_cfg, chat_id, message_id, "❌ 找不到主机配置，可能已被删除或修改。")
            return

        try:
            containers = await cls._list_containers(host)
        except Exception as e:
            logger.error(sanitize(f"❌ [TG Bot] 获取容器列表失败: {e}"))
            await cls._render(bot_cfg, chat_id, message_id, f"❌ 获取容器列表失败: {esc(e)}")
            return

        # 按名称排序，保证分页翻页时顺序稳定
        containers.sort(key=lambda c: str(c.get("name", "")))
        total = len(containers)
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        start = page * PAGE_SIZE
        page_items = containers[start:start + PAGE_SIZE]

        text = f"🖥 主机 {b(host.get('name'))} 的容器列表（共 {total} 个）\n第 {page + 1}/{total_pages} 页"
        buttons = [
            [{
                "text": f"{'🟢' if c.get('status') == 'running' else '🔴'} {c.get('name')}",
                "callback_data": f"ci:{host_id}:{c['id']}:{page}",
            }]
            for c in page_items
        ]

        nav = []
        if page > 0:
            nav.append({"text": "◀️ 上一页", "callback_data": f"hl:{host_id}:{page - 1}"})
        if page < total_pages - 1:
            nav.append({"text": "下一页 ▶️", "callback_data": f"hl:{host_id}:{page + 1}"})
        if nav:
            buttons.append(nav)
        buttons.append([{"text": "⬅️ 返回主机列表", "callback_data": "hosts_back"}])
        await cls._render(bot_cfg, chat_id, message_id, text, {"inline_keyboard": buttons})

    @classmethod
    async def _build_container_detail(cls, host: Dict, container_id: str, page: int = 0) -> Tuple[Optional[str], Optional[list]]:
        """构建容器详情文本与按钮，返回 (text, buttons)；容器不存在时返回 (None, None)。"""
        containers = await cls._list_containers(host)
        c = next(
            (item for item in containers if item["id"] == container_id or item.get("full_id") == container_id),
            None,
        )
        if not c:
            return None, None

        display_status = STATUS_MAP.get(str(c.get("status", "")).lower(), c.get("status", "unknown"))
        # 附带时间戳：保证"刷新详情"每次内容有变化（避免 TG "message is not modified"）
        text = (
            f"📦 {b('容器详情')}\n\n"
            f"名称: {code(c.get('name'))}\n"
            f"镜像: {code(c.get('image'))}\n"
            f"状态: {code(display_status)}\n"
            f"ID: {code(c.get('id'))}\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )

        host_id = host.get("id")
        buttons = []
        if c.get("status") == "running":
            buttons.append([
                {"text": "🛑 停止", "callback_data": f"co:{host_id}:{container_id}:stop:{page}"},
                {"text": "🔄 重启", "callback_data": f"co:{host_id}:{container_id}:restart:{page}"},
            ])
        else:
            buttons.append([{"text": "▶️ 启动", "callback_data": f"co:{host_id}:{container_id}:start:{page}"}])
        buttons.append([{"text": "🆙 更新容器 (Pull & Recreate)", "callback_data": f"co:{host_id}:{container_id}:update:{page}"}])
        buttons.append([
            {"text": "🔄 刷新详情", "callback_data": f"ci:{host_id}:{container_id}:{page}"},
            {"text": "⬅️ 返回列表", "callback_data": f"hl:{host_id}:{page}"},
        ])
        return text, buttons

    @classmethod
    async def _show_container_detail(cls, bot_cfg: Dict, chat_id: str, host_id: str, container_id: str, page: int = 0, message_id: Optional[int] = None):
        host = cls._get_host(host_id)
        if not host:
            await cls._render(bot_cfg, chat_id, message_id, "❌ 找不到主机配置，可能已被删除或修改。")
            return

        try:
            text, buttons = await cls._build_container_detail(host, container_id, page)
        except Exception as e:
            logger.error(sanitize(f"❌ [TG Bot] 获取容器详情失败: {e}"))
            await cls._render(bot_cfg, chat_id, message_id, f"❌ 获取容器详情失败: {esc(e)}")
            return

        if not text:
            await cls._render(
                bot_cfg, chat_id, message_id,
                "❌ 找不到该容器，可能已被删除或重建。",
                {"inline_keyboard": [[{"text": "⬅️ 返回列表", "callback_data": f"hl:{host_id}:{page}"}]]},
            )
            return

        await cls._render(bot_cfg, chat_id, message_id, text, {"inline_keyboard": buttons})

    @classmethod
    async def _request_container_op(cls, bot_cfg: Dict, chat_id: str, message_id: Optional[int], host_id: str, container_id: str, op: str, page: int):
        """发起容器操作：破坏性操作先进入确认页，其余直接执行。"""
        if op not in CONTAINER_OPS:
            return
        if op in DESTRUCTIVE_OPS and not cls._is_trusted_chat(bot_cfg, chat_id):
            await cls._render(bot_cfg, chat_id, message_id, "⛔ 出于安全考虑，容器操作仅允许在与 Bot 配置一致的会话中执行。")
            return

        if op in DESTRUCTIVE_OPS:
            await cls._show_op_confirm(bot_cfg, chat_id, message_id, host_id, container_id, op, page)
        else:
            await cls._exec_container_op(bot_cfg, chat_id, message_id, host_id, container_id, op, page)

    @classmethod
    async def _show_op_confirm(cls, bot_cfg: Dict, chat_id: str, message_id: Optional[int], host_id: str, container_id: str, op: str, page: int):
        """破坏性操作二次确认页。"""
        name = container_id
        host = cls._get_host(host_id)
        if host:
            try:
                containers = await cls._list_containers(host)
                c = next(
                    (item for item in containers if item["id"] == container_id or item.get("full_id") == container_id),
                    None,
                )
                if c:
                    name = c.get("name") or container_id
            except Exception:
                pass

        text = (
            f"⚠️ {b('操作确认')}\n\n"
            f"容器: {code(name)}\n"
            f"操作: {code(op)}\n\n"
            f"{OP_WARNINGS.get(op, '')}\n\n"
            "确定要执行吗？"
        )
        buttons = [[
            {"text": "✅ 确认执行", "callback_data": f"cf:{host_id}:{container_id}:{op}:{page}"},
            {"text": "❌ 取消", "callback_data": f"ci:{host_id}:{container_id}:{page}"},
        ]]
        await cls._render(bot_cfg, chat_id, message_id, text, {"inline_keyboard": buttons})

    @classmethod
    async def _exec_container_op(cls, bot_cfg: Dict, chat_id: str, message_id: Optional[int], host_id: str, container_id: str, op: str, page: int = 0):
        """执行容器操作，全程原地编辑同一条消息反馈进度与结果。"""
        if op not in CONTAINER_OPS:
            return
        # 安全：破坏性操作仅允许在 Bot 配置的通知会话中触发
        if op in DESTRUCTIVE_OPS and not cls._is_trusted_chat(bot_cfg, chat_id):
            await cls._render(bot_cfg, chat_id, message_id, "⛔ 出于安全考虑，容器操作仅允许在与 Bot 配置一致的会话中执行。")
            return

        host = cls._get_host(host_id)
        if not host:
            await cls._render(bot_cfg, chat_id, message_id, "❌ 找不到主机配置，可能已被删除或修改。")
            return
        # 构造函数含同步 ping，需在线程池中实例化
        service = await asyncio.to_thread(DockerService, host)

        # 记录容器名称，因为更新后 ID 会变
        container_name = None
        try:
            containers = await asyncio.to_thread(service.list_containers)
            c_old = next(
                (item for item in containers if item["id"] == container_id or item.get("full_id") == container_id),
                None,
            )
            if c_old:
                container_name = c_old.get("name")
        except Exception:
            pass

        display_name = container_name or container_id[:12]
        await cls._render(
            bot_cfg, chat_id, message_id,
            f"⏳ 正在执行 {code(op)} 操作（{code(display_name)}），请稍候...",
        )
        await get_client(bot_cfg.get("token")).send_chat_action(chat_id, "typing")

        error_text = ""
        try:
            success = await asyncio.to_thread(service.container_action, container_id, op)
        except Exception as e:
            success = False
            error_text = sanitize(str(e))

        if not success:
            detail = f": {esc(error_text)}" if error_text else ""
            await cls._render(bot_cfg, chat_id, message_id, f"❌ 操作 {code(op)} 执行失败{detail}")
            return

        # recreate/update 后容器 ID 会变，按名称追踪新 ID
        target_id = container_id
        if op in ("recreate", "update") and container_name:
            try:
                await asyncio.sleep(1)
                new_containers = await asyncio.to_thread(service.list_containers)
                c_new = next((item for item in new_containers if item.get("name") == container_name), None)
                if c_new:
                    target_id = c_new["id"]
                    logger.info(f"🔄 [TG Bot] 容器 {container_name} ID 已更新: {container_id} -> {target_id}")
            except Exception:
                pass

        # 成功后原地刷新为最新详情（带结果前缀）
        try:
            text, buttons = await cls._build_container_detail(host, target_id, page)
        except Exception as e:
            logger.error(sanitize(f"❌ [TG Bot] 刷新容器详情失败: {e}"))
            text, buttons = None, None

        if text:
            await cls._render(
                bot_cfg, chat_id, message_id,
                f"✅ {code(op)} 执行成功\n\n{text}",
                {"inline_keyboard": buttons},
            )
        else:
            await cls._render(
                bot_cfg, chat_id, message_id,
                f"✅ 操作 {code(op)} 执行成功！（容器状态已变化，请返回列表刷新查看）",
                {"inline_keyboard": [[{"text": "⬅️ 返回列表", "callback_data": f"hl:{host_id}:{page}"}]]},
            )

    # ---------- 发送 ----------

    @staticmethod
    async def _send_message(bot_cfg: Dict, chat_id: str, text: str, reply_markup: Optional[Dict] = None):
        try:
            await get_client(bot_cfg.get("token")).send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(sanitize(f"❌ [TG Bot] 发送消息失败: {e}"))

    @staticmethod
    async def _edit_message(bot_cfg: Dict, chat_id: str, message_id: int, text: str, reply_markup: Optional[Dict] = None):
        try:
            await get_client(bot_cfg.get("token")).edit_message(chat_id, message_id, text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(sanitize(f"❌ [TG Bot] 编辑消息失败: {e}"))
