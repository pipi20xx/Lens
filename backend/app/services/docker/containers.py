"""容器操作：列表、统计、动作（启停/重构）、日志、终端 socket。

性能说明（改前 → 改后，以 20 个容器为例）：
- 列表：docker-py `containers.list()` 默认会为每个容器再各发一次 inspect_container，
  循环里访问 `c.image.tags` 又各发一次 inspect_image → 1+2N = 41 次走 SSH 隧道的
  HTTP 往返。改用 `sparse=True` 后只发 1 次（/containers/json）。
- 统计：`docker stats --no-stream` 在 daemon 侧会丢弃第一帧、等第二帧才返回
  （moby daemon/stats.go: noStreamFirstFrame），且 CLI 从不传 one-shot，
  因此**固定 ~2 秒**。改为一次 exec 直读 cgroup，稳态下复用上次采样做差。
"""
import json
import threading
import time

from typing import List, Dict, Any

from app.utils.logger import logger

from .base import DockerServiceBase


def _to_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class ContainerOpsMixin(DockerServiceBase):
    _containers_cache = {}  # { "host_all_details": (data, timestamp) }
    _stats_cache = {}       # { host_id: (data, timestamp) }  同一主机短时间内的并发请求共享结果
    _stats_prev = {}        # { host_id: {"ts":, "host_cpu":, "cpu": {name: usec}} }
    _stats_locks = {}
    _stats_locks_guard = threading.Lock()

    # ------------------------------------------------------------- 缓存工具
    @classmethod
    def _stats_lock(cls, host_id: str) -> threading.Lock:
        with cls._stats_locks_guard:
            lock = cls._stats_locks.get(host_id)
            if lock is None:
                lock = threading.Lock()
                cls._stats_locks[host_id] = lock
            return lock

    def _containers_cache_key(self, all, details) -> str:
        return f"{self.host_id}_{all}_{details}"

    def _invalidate_containers_cache(self):
        """按 host 前缀清理。改前这里写的是 f"{host_id}_True"，和写入时的
        f"{host_id}_{all}_{details}" 对不上，导致缓存永远清不掉。"""
        prefix = f"{self.host_id}_"
        for key in [k for k in self._containers_cache if k.startswith(prefix)]:
            self._containers_cache.pop(key, None)
        self._stats_cache.pop(self.host_id, None)

    # --------------------------------------------------------------- 列表
    @staticmethod
    def _sparse_name(attrs: Dict[str, Any]) -> str:
        """sparse 对象的 attrs['Name'] 不存在，只有 Names 列表。"""
        name = attrs.get("Name")
        if name:
            return name.lstrip("/")
        names = attrs.get("Names") or []
        return names[0].lstrip("/") if names else ""

    @staticmethod
    def _sparse_ports(attrs: Dict[str, Any]) -> Dict[str, Any]:
        """把 /containers/json 的 Ports 数组还原成 inspect 的 Ports 字典形状。

        前端 getPortBindings() 依赖 { "80/tcp": [{"HostPort": "8080"}], ... } 这个结构。
        """
        network_settings = attrs.get("NetworkSettings") or {}
        if isinstance(network_settings.get("Ports"), dict):
            return network_settings["Ports"]  # 拿到的是完整 inspect，直接用

        ports: Dict[str, Any] = {}
        for item in attrs.get("Ports") or []:
            public = item.get("PublicPort")
            if not public:
                continue
            key = f"{item.get('PrivatePort')}/{item.get('Type') or 'tcp'}"
            ports.setdefault(key, []).append({
                "HostIp": item.get("IP", ""),
                "HostPort": str(public),
            })
        return ports

    def list_containers(self, all=True, filters: Dict[str, Any] = None, details: bool = True) -> List[Dict[str, Any]]:
        # 只有在没有过滤条件的情况下使用 5 秒缓存，防止前端频繁切换/请求
        cache_key = self._containers_cache_key(all, details)
        if not filters and cache_key in self._containers_cache:
            data, ts = self._containers_cache[cache_key]
            if time.time() - ts < 5:
                return data

        results = []

        # 优先尝试通过 docker-py 客户端获取（效率高，数据全）
        if self.client:
            try:
                # sparse=True：直接从 /containers/json 构造对象，跳过逐容器 inspect + image inspect
                containers = self.client.containers.list(all=all, filters=filters, sparse=True)
                for c in containers:
                    attrs = c.attrs or {}

                    ip = ""
                    if details:
                        networks = (attrs.get("NetworkSettings") or {}).get("Networks") or {}
                        if networks:
                            # 优先找 bridge 或者第一个
                            if "bridge" in networks:
                                ip = (networks["bridge"] or {}).get("IPAddress", "")
                            if not ip:
                                ip = (next(iter(networks.values())) or {}).get("IPAddress", "")

                    results.append({
                        "id": c.short_id,
                        "full_id": c.id,
                        "name": self._sparse_name(attrs),
                        "image": attrs.get("Image") or "",
                        # sparse 下 c.status 同样可用（Container.status 兼容字符串 State）
                        "status": c.status,
                        # /containers/json 没有 State.StartedAt，直接用 "Up 2 hours" 这种
                        # Status 字符串；前端 formatUptime() 正是按 "Up " 前缀转中文的
                        "uptime": attrs.get("Status") or c.status,
                        "created": attrs.get("Created"),
                        "ports": self._sparse_ports(attrs),
                        "ip": ip,
                    })

                # 获取结果后存入缓存并返回
                if not filters:
                    self._containers_cache[cache_key] = (results, time.time())
                return results
            except Exception as e:
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py client failed, falling back to SSH Shell: {e}")

        # 如果客户端不可用或报错，通过 SSH 执行 docker ps 命令解析 (纯 SSH 模式)
        if self.host_config.get("type") == "ssh" or self.host_config.get("type") == "local":
            cmd = "docker ps -a --format '{{json .}}'" if all else "docker ps --format '{{json .}}'"
            res = self.exec_command(cmd)
            if res["success"]:
                try:
                    results = []
                    lines = res["stdout"].strip().split('\n')
                    for line in lines:
                        if not line: continue
                        c = json.loads(line)
                        results.append({
                            "id": c.get("ID"),
                            "full_id": c.get("ID"),
                            "name": c.get("Names"),
                            "image": c.get("Image"),
                            "status": c.get("Status").lower().split(' ')[0], # "Up 2 hours" -> "up"
                            "uptime": c.get("Status"), # 包含 "Up 2 hours"
                            "created": c.get("CreatedAt"),
                            "ports": c.get("Ports"),
                            "ip": "" # 稍后补充
                        })

                    # 补充 IP 信息
                    if details:
                        ip_cmd = "docker inspect --format '{{.Name}}:{{range .NetworkSettings.Networks}}{{.IPAddress}},{{end}}' $(docker ps -aq)"
                        ip_res = self.exec_command(ip_cmd, log_error=False)
                        if ip_res["success"]:
                            ip_map = {}
                            for line in ip_res["stdout"].strip().split('\n'):
                                if ':' in line:
                                    name, ips = line.split(':', 1)
                                    name = name.lstrip('/')
                                    ip_list = [ip for ip in ips.split(',') if ip]
                                    ip_map[name] = ip_list[0] if ip_list else ""

                            for r in results:
                                r["ip"] = ip_map.get(r["name"], "")

                    if not filters:
                        self._containers_cache[cache_key] = (results, time.time())
                    return results
                except Exception as e:
                    logger.error(f"Failed to parse docker ps output: {e}")

        return results

    # --------------------------------------------------------------- 统计
    @staticmethod
    def _human_size(value) -> str:
        """对齐 docker stats 的显示格式，例如 745.2MiB / 35.05GiB"""
        try:
            num = float(value or 0)
        except (TypeError, ValueError):
            return "0B"
        for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
            if num < 1024 or unit == "PiB":
                return f"{int(num)}B" if unit == "B" else f"{num:.4g}{unit}"
            num /= 1024
        return f"{num:.4g}PiB"

    # 远端只读采集脚本：一次 exec 拿到所有运行中容器的 cgroup 数据。
    # 同时兼容 cgroup v2 / v1 与 systemd / cgroupfs 两种驱动；读不到就由调用方回退 CLI。
    # __SLEEP__ 为 0 时只依赖"上一次快照做差"，为 0.5 时在远端采两份自给自足。
    _CGROUP_STATS_SCRIPT = r"""
CG=/sys/fs/cgroup
V2=0
[ -f "$CG/cgroup.controllers" ] && V2=1
MT=$(awk '/^MemTotal:/{print $2*1024; exit}' /proc/meminfo 2>/dev/null)
NP=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
LIST=$(docker ps --no-trunc --format '{{.ID}}|{{.Names}}' 2>/dev/null)
snap() {
  P="$1"
  HT=0
  for v in $(head -n 1 /proc/stat 2>/dev/null); do
    case "$v" in cpu) ;; *) HT=$((HT + v)) ;; esac
  done
  echo "H|$P|$HT|$MT|$NP|$V2"
  echo "$LIST" | while IFS='|' read -r CID CNAME; do
    [ -z "$CID" ] && continue
    if [ "$V2" = "1" ]; then
      D=""
      for c in "$CG/system.slice/docker-$CID.scope" "$CG/docker/$CID"; do
        [ -d "$c" ] && { D="$c"; break; }
      done
      [ -z "$D" ] && continue
      MEM=$(cat "$D/memory.current" 2>/dev/null)
      LIM=$(cat "$D/memory.max" 2>/dev/null)
      CPUC=$(awk '/^usage_usec/{print $2; exit}' "$D/cpu.stat" 2>/dev/null)
      PIDS=$(cat "$D/pids.current" 2>/dev/null)
      IO=$(awk '{for(i=1;i<=NF;i++){if($i ~ /^rbytes=/){split($i,a,"=");r+=a[2]} if($i ~ /^wbytes=/){split($i,a,"=");w+=a[2]}}} END{printf "%d", r+w}' "$D/io.stat" 2>/dev/null)
      PID=$(head -n 1 "$D/cgroup.procs" 2>/dev/null)
    else
      DM=""; DC=""; DP=""
      for c in "$CG/memory/docker/$CID" "$CG/memory/system.slice/docker-$CID.scope"; do
        [ -d "$c" ] && { DM="$c"; break; }
      done
      for c in "$CG/cpuacct/docker/$CID" "$CG/cpuacct/system.slice/docker-$CID.scope" "$CG/cpu,cpuacct/docker/$CID"; do
        [ -d "$c" ] && { DC="$c"; break; }
      done
      for c in "$CG/pids/docker/$CID" "$CG/pids/system.slice/docker-$CID.scope"; do
        [ -d "$c" ] && { DP="$c"; break; }
      done
      MEM=$(cat "$DM/memory.usage_in_bytes" 2>/dev/null)
      LIM=$(cat "$DM/memory.limit_in_bytes" 2>/dev/null)
      CPUNS=$(cat "$DC/cpuacct.usage" 2>/dev/null)
      CPUC=$(( ${CPUNS:-0} / 1000 ))
      PIDS=$(cat "$DP/pids.current" 2>/dev/null)
      IO=0
      PID=$(head -n 1 "$DM/cgroup.procs" 2>/dev/null)
    fi
    NB=0
    if [ -n "$PID" ] && [ -r "/proc/$PID/net/dev" ]; then
      NB=$(awk -F'[: ]+' 'NR>2{r+=$3;t+=$11} END{printf "%d", r+t}' "/proc/$PID/net/dev" 2>/dev/null)
    fi
    printf 'C|%s|%s|%s|%s|%s|%s|%s|%s\n' "$P" "$CNAME" "${MEM:-0}" "${LIM:-0}" "${CPUC:-0}" "${PIDS:-0}" "${IO:-0}" "${NB:-0}"
  done
}
snap A
sleep __SLEEP__
snap B
true
"""

    @staticmethod
    def _parse_stats_snapshot(text: str):
        """把脚本输出拆成 A / B 两份快照。"""
        snaps: Dict[str, Any] = {}
        for line in (text or "").splitlines():
            parts = line.split("|")
            if len(parts) >= 6 and parts[0] == "H":
                phase = parts[1]
                if phase in ("A", "B"):
                    snaps[phase] = {
                        "host_cpu": _to_int(parts[2]),
                        "mem_total": _to_int(parts[3]),
                        "ncpu": _to_int(parts[4]) or 1,
                        "v2": _to_int(parts[5]),
                        "containers": {},
                    }
            elif len(parts) >= 9 and parts[0] == "C":
                snap = snaps.get(parts[1])
                if snap is None:
                    continue
                snap["containers"][parts[2]] = {
                    "mem": _to_int(parts[3]),
                    "mem_limit": _to_int(parts[4]),
                    "cpu_usec": _to_int(parts[5]),
                    "pids": _to_int(parts[6]),
                    "io": _to_int(parts[7]),
                    "net": _to_int(parts[8]),
                }
        return snaps.get("A"), snaps.get("B")

    def _collect_stats_cgroup(self, now: float):
        """一次 exec 直读 cgroup。返回 None 表示不可用，调用方回退 CLI。"""
        prev = self._stats_prev.get(self.host_id)
        use_prev = bool(prev) and (now - prev["ts"]) <= 30
        # 有新鲜基线就不用在远端等；没有就现场采两份（0.5s，仍远低于 docker stats 的 2s）
        sleep_s = "0" if use_prev else "0.5"
        script = self._CGROUP_STATS_SCRIPT.replace("__SLEEP__", sleep_s)

        res = self.exec_command(script, log_error=False, timeout=30)
        if not res.get("success"):
            return None

        snap_a, snap_b = self._parse_stats_snapshot(res.get("stdout", ""))
        if not snap_b:
            return None
        # 一个容器都没解析出来：多半是 cgroup 布局和预期不符（而不是真的没有容器）。
        # 宁慢勿错，退回 CLI 路径。真的没有运行中容器时，docker stats 也会立刻返回空。
        if not snap_b["containers"]:
            return None

        if use_prev:
            base_host_cpu = prev["host_cpu"]
            base_cpu = prev["cpu"]
        else:
            if not snap_a:
                return None
            base_host_cpu = snap_a["host_cpu"]
            base_cpu = {name: s["cpu_usec"] for name, s in snap_a["containers"].items()}

        host_delta = snap_b["host_cpu"] - base_host_cpu
        if host_delta <= 0:
            # 采样窗口无效（例如远端 sleep 不支持小数），交给 CLI 兜底，宁慢勿错
            return None

        ncpu = snap_b["ncpu"] or 1
        host_mem_total = snap_b["mem_total"] or 0
        stats: Dict[str, Any] = {}

        for name, s in snap_b["containers"].items():
            if use_prev and name not in base_cpu:
                cpu_pct = 0.0  # 新容器还没有基线，下一次轮询就正常了
            else:
                delta = s["cpu_usec"] - base_cpu.get(name, 0)
                if delta < 0:
                    delta = 0  # 计数器被重置
                # /proc/stat 的单位是 USER_HZ(100) 的 jiffy，换算成微秒后与 cpu_usec 同量纲
                cpu_pct = delta / (host_delta * 10000.0) * ncpu * 100.0
                cpu_pct = max(0.0, min(cpu_pct, ncpu * 100.0))

            limit = s["mem_limit"]
            if limit <= 0 or (host_mem_total and limit > host_mem_total):
                limit = host_mem_total  # 未限制内存时，docker 也显示宿主机总量
            mem_pct = (s["mem"] / limit * 100.0) if limit else 0.0

            stats[name] = {
                "cpu": f"{cpu_pct:.2f}%",
                "mem": f"{self._human_size(s['mem'])} / {self._human_size(limit)}",
                "mem_perc": f"{mem_pct:.2f}%",
                "net": self._human_size(s["net"]),
                "block": self._human_size(s["io"]),
                "pids": str(s["pids"]),
            }

        self._stats_prev[self.host_id] = {
            "ts": now,
            "host_cpu": snap_b["host_cpu"],
            "cpu": {name: s["cpu_usec"] for name, s in snap_b["containers"].items()},
        }
        return stats

    def _collect_stats_cli(self) -> Dict[str, Any]:
        """兜底路径。注意：docker stats --no-stream 在 daemon 侧固定要等两帧（~2s），
        而且 CLI 没有 one-shot 选项，所以这条路无法再优化，只作为降级使用。"""
        cmd = "docker stats --no-stream --format '{{json .}}'"
        res = self.exec_command(cmd, log_error=False)
        stats = {}
        if res["success"]:
            try:
                lines = res["stdout"].strip().split('\n')
                for line in lines:
                    if not line: continue
                    try:
                        s = json.loads(line)
                        name = s.get("Name")
                        if name:
                            stats[name] = {
                                "cpu": s.get("CPUPerc"),
                                "mem": s.get("MemUsage"),
                                "mem_perc": s.get("MemPerc"),
                                "net": s.get("NetIO"),
                                "block": s.get("BlockIO"),
                                "pids": s.get("PIDs")
                            }
                    except Exception: continue
            except Exception as e:
                logger.error(f"Failed to parse docker stats: {e}")
        return stats

    def get_containers_stats(self) -> Dict[str, Any]:
        """获取所有容器的实时资源占用。

        同一主机加锁做单飞：多个浏览器标签页同时轮询只会产生一次真实采集。
        """
        host_id = self.host_id
        cached = self._stats_cache.get(host_id)
        if cached and time.time() - cached[1] < 2:
            return cached[0]

        with self._stats_lock(host_id):
            cached = self._stats_cache.get(host_id)
            if cached and time.time() - cached[1] < 2:
                return cached[0]

            stats = None
            try:
                stats = self._collect_stats_cgroup(time.time())
            except Exception as e:
                logger.warning(f"[Docker] cgroup 采集异常，回退 docker stats: {e}")

            if stats is None:
                stats = self._collect_stats_cli()

            self._stats_cache[host_id] = (stats, time.time())
            return stats

    # --------------------------------------------------------------- 操作
    def container_action(self, container_id: str, action: str):
        if not self.client:
            raise Exception("Docker client not initialized")

        try:
            # 每次操作前重新获取容器对象，确保状态最新且连接有效
            try:
                container = self.client.containers.get(container_id)
            except Exception as e:
                raise Exception(f"无法找到容器 {container_id[:12]}: {e}")

            if action == "start": container.start()
            elif action == "stop": container.stop()
            elif action == "restart": container.restart()
            elif action == "remove": container.remove(force=True)
            elif action in ["recreate", "update"]:
                attrs = container.attrs
                image_tag = attrs['Config']['Image']
                name = attrs['Name'].lstrip('/')

                # 无论 recreate 还是 update，都执行 pull（保持与网页版逻辑一致）
                logger.info(f"📥 [Docker] 正在为容器 {name} 拉取最新镜像: {image_tag}")
                try:
                    self.client.images.pull(image_tag)
                except Exception as e:
                    # 更新操作中，pull 失败即视为整体失败，立即中止以保护原容器
                    raise Exception(f"镜像更新失败: 无法拉取最新镜像 ({e})。操作已终止，原容器未受影响。")

                # 提取完整配置
                config = attrs.get('Config', {})
                host_config = attrs.get('HostConfig', {})

                # --- 修复：保留挂载的 Propagation 属性 (如 rslave) ---
                mounts = attrs.get('Mounts', [])
                current_binds = host_config.get('Binds') or []
                final_binds = []

                bind_map = {}
                for b in current_binds:
                    parts = b.split(':')
                    if len(parts) >= 2:
                        key = f"{parts[0]}:{parts[1]}"
                        mode = parts[2] if len(parts) > 2 else ""
                        bind_map[key] = mode

                for m in mounts:
                    if m.get('Type') == 'bind':
                        src = m.get('Source')
                        dst = m.get('Destination')
                        propagation = m.get('Propagation', '')
                        if propagation and propagation != 'rprivate':
                            key = f"{src}:{dst}"
                            if key in bind_map:
                                mode = bind_map[key]
                                if propagation not in mode:
                                    new_mode = f"{mode},{propagation}" if mode else propagation
                                    bind_map[key] = new_mode
                            else:
                                rw_mode = "rw" if m.get('RW', True) else "ro"
                                bind_map[key] = f"{rw_mode},{propagation}"

                if not bind_map and current_binds:
                    final_binds = current_binds
                else:
                    for key, mode in bind_map.items():
                        if mode:
                            final_binds.append(f"{key}:{mode}")
                        else:
                            final_binds.append(key)

                port_bindings = host_config.get('PortBindings') or {}
                ports = {}
                if port_bindings:
                    for container_port, host_ports in port_bindings.items():
                        if host_ports:
                            ports[container_port] = host_ports[0].get('HostPort')

                network_mode = host_config.get('NetworkMode', 'bridge')
                if network_mode == "host":
                    ports = None

                create_kwargs = {
                    "image": image_tag,
                    "name": name,
                    "detach": True,
                    "environment": config.get('Env', []),
                    "volumes": final_binds,
                    "ports": ports,
                    "restart_policy": host_config.get('RestartPolicy', {}),
                    "network_mode": network_mode,
                    "command": config.get('Cmd'),
                    "entrypoint": config.get('Entrypoint'),
                    "working_dir": config.get('WorkingDir'),
                    "user": config.get('User'),
                    "hostname": config.get('Hostname'),
                    "mac_address": config.get('MacAddress'),
                    "labels": config.get('Labels')
                }

                if host_config.get('Privileged'):
                    create_kwargs["privileged"] = True

                old_name = container.name
                bak_name = f"{old_name}_lens_bak_{int(time.time())}"

                try:
                    # 再次确认容器还在且连接有效
                    container = self.client.containers.get(container_id)
                    container.stop()
                    container.rename(bak_name)

                    # 创建并启动新容器
                    self.client.containers.run(**create_kwargs)

                    # 新容器启动成功，删除备份
                    container.remove(force=True)
                    logger.info(f"✨ [Docker] 容器 {old_name} 重构成功，已清理旧容器")
                except Exception as run_err:
                    logger.error(f"❌ [Docker] 新容器启动失败，尝试回滚: {run_err}")
                    try:
                        # 检查新容器是否已半途创建（如果创建了但没启动成功，也需要清理掉名称占位）
                        try:
                            failed_new = self.client.containers.get(old_name)
                            failed_new.remove(force=True)
                        except Exception: pass

                        # 尝试找回备份容器（可能因为连接问题导致 container 对象失效）
                        try:
                            bak_container = self.client.containers.get(bak_name)
                            bak_container.rename(old_name)
                            bak_container.start()
                            logger.info(f"⏪ [Docker] 已成功回滚至旧容器 {old_name}")
                        except Exception as e:
                            # 如果 rename 失败，原 container 对象可能还有效
                            container.rename(old_name)
                            container.start()
                            logger.info(f"⏪ [Docker] 已成功回滚至旧容器 {old_name}")
                    except Exception as rollback_err:
                        logger.error(f"🚨 [Docker] 回滚失败! 旧容器目前名称为 {bak_name}: {rollback_err}")
                        raise Exception(f"容器启动失败: {run_err}。回滚也失败了，请手动检查宿主机上名为 {bak_name} 的备份容器。")
                    raise run_err

            # 操作后清理列表缓存与统计缓存
            self._invalidate_containers_cache()

            return True
        except Exception as e:
            logger.error(f"Error performing action {action} on container {container_id}: {e}")
            raise e

    def get_container_logs(self, container_id: str, tail=100) -> str:
        if not self.client: return "Not connected to Docker"
        try:
            container = self.client.containers.get(container_id)
            return container.logs(tail=tail).decode("utf-8")
        except Exception as e:
            return str(e)

    def get_container_socket(self, container_id: str, command: str = "/bin/bash"):
        """获取容器的交互式 Socket"""
        if not self.client:
            return None

        try:
            # 使用 APIClient 以获得对底层 socket 的访问权限
            api_client = self.client.api
            exec_instance = api_client.exec_create(
                container_id,
                cmd=command,
                stdin=True,
                stdout=True,
                stderr=True,
                tty=True
            )

            # 返回 socket 供 WebSocket 使用
            sock = api_client.exec_start(exec_instance['Id'], detach=False, tty=True, stream=True, socket=True)
            return sock
        except Exception as e:
            logger.error(f"Failed to create exec socket: {e}")
            if command == "/bin/bash":
                # 尝试退回到 /bin/sh
                return self.get_container_socket(container_id, "/bin/sh")
            return None
