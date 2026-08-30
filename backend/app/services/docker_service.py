import docker
import paramiko
import os
import re
import json
import time
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from app.utils.logger import logger
from app.core.config_manager import get_config

# --- 深度补丁：彻底解决 known_hosts 和 密码支持问题 ---

# 1. 强制策略补丁：禁止拒绝新主机
_original_set_policy = paramiko.SSHClient.set_missing_host_key_policy
def _forced_set_policy(self, policy):
    return _original_set_policy(self, paramiko.AutoAddPolicy())
paramiko.SSHClient.set_missing_host_key_policy = _forced_set_policy

# 2. 密码注入补丁
_original_connect = paramiko.SSHClient.connect
def _patched_connect(self, hostname, port=22, username=None, password=None, **kwargs):
    if not password:
        config = get_config()
        hosts = config.get("docker_hosts", [])
        host_match = next((h for h in hosts if h.get("ssh_host") == hostname), None)
        if host_match and host_match.get("ssh_pass"):
            password = host_match.get("ssh_pass")
    
    kwargs['allow_agent'] = False
    kwargs['look_for_keys'] = False
    return _original_connect(self, hostname, port=port, username=username, password=password, **kwargs)

paramiko.SSHClient.connect = _patched_connect

# --- Service 实现 ---

class DockerService:
    # 类级别缓存：{ host_id: (client, timestamp) }
    _clients_cache = {}
    _ssh_clients_cache = {} # { host_id: (ssh_client, timestamp) }
    _containers_cache = {} # { host_id: (data, timestamp) }
    _projects_cache = {} # { host_id: (data, timestamp) }
    _images_cache = {} # { host_id: (data, timestamp) }
    _pull_tasks = {} # { task_id: {...} } 镜像拉取任务进度（全主机共享，task_id 含 host 前缀）
    
    def __init__(self, host_config: Dict[str, Any]):
        self.host_config = host_config
        self.host_id = host_config.get("id", "local")
        self.client = self._get_client()

    def _get_client(self):
        # 检查有效缓存 (30分钟内有效)
        if self.host_id in self._clients_cache:
            client, ts = self._clients_cache[self.host_id]
            if time.time() - ts < 1800:
                try:
                    # 快速检查连接是否真的存活
                    client.ping()
                    return client
                except:
                    if self.host_id in self._clients_cache:
                        del self._clients_cache[self.host_id]
        
        try:
            client = None
            host_type = self.host_config.get("type", "local")
            if host_type == "local":
                client = docker.from_env()
            
            elif host_type == "ssh":
                ssh_host = self.host_config.get("ssh_host")
                ssh_user = self.host_config.get("ssh_user", "root")
                ssh_port = self.host_config.get("ssh_port", 22)
                # 使用 timeout 避免卡死
                base_url = f"ssh://{ssh_user}@{ssh_host}:{ssh_port}"
                client = docker.DockerClient(base_url=base_url, use_ssh_client=False, timeout=60)
            
            elif host_type == "tcp":
                host = self.host_config.get("ssh_host")
                port = self.host_config.get("ssh_port", 2375)
                use_tls = self.host_config.get("use_tls", False)
                protocol = "https" if use_tls else "http"
                base_url = f"{protocol}://{host}:{port}"
                client = docker.DockerClient(base_url=base_url, timeout=60)
            
            if client:
                self._clients_cache[self.host_id] = (client, time.time())
                return client
                
            return None
        except Exception as e:
            logger.error(f"Failed to connect to Docker host {self.host_config.get('name')}: {e}")
            return None

    def list_containers(self, all=True, filters: Dict[str, Any] = None, details: bool = True) -> List[Dict[str, Any]]:
        # 只有在没有过滤条件的情况下使用 5 秒缓存，防止前端频繁切换/请求
        cache_key = f"{self.host_id}_{all}_{details}"
        if not filters and cache_key in self._containers_cache:
            data, ts = self._containers_cache[cache_key]
            if time.time() - ts < 5:
                return data

        results = []

        # 优先尝试通过 docker-py 客户端获取（效率高，数据全）
        if self.client:
            try:
                # 传入 filters 参数
                containers = self.client.containers.list(all=all, filters=filters)
                for c in containers:
                    ip = ""
                    uptime_str = c.status
                    
                    if details:
                        networks = c.attrs.get("NetworkSettings", {}).get("Networks", {})
                        if networks:
                            # 优先找 bridge 或者第一个
                            if "bridge" in networks:
                                ip = networks["bridge"].get("IPAddress", "")
                            if not ip:
                                ip = next(iter(networks.values())).get("IPAddress", "")

                        # 计算运行时间
                        import datetime
                        started_at = c.attrs.get("State", {}).get("StartedAt", "")
                        if started_at and c.status == "running":
                            try:
                                # 2024-05-22T08:34:11.123456789Z -> 2024-05-22T08:34:11
                                t_part = started_at.split('.')[0].replace('Z', '')
                                start_dt = datetime.datetime.fromisoformat(t_part)
                                delta = datetime.datetime.utcnow() - start_dt
                                days = delta.days
                                hours, remainder = divmod(delta.seconds, 3600)
                                minutes, _ = divmod(remainder, 60)
                                if days > 0: uptime_str = f"已运行 {days} 天"
                                elif hours > 0: uptime_str = f"已运行 {hours} 小时"
                                else: uptime_str = f"已运行 {minutes} 分钟"
                            except: pass

                    results.append({
                        "id": c.short_id,
                        "full_id": c.id,
                        "name": c.name,
                        "image": c.image.tags[0] if c.image.tags else c.image.id,
                        "status": c.status,
                        "uptime": uptime_str,
                        "created": c.attrs.get("Created"),
                        "ports": c.attrs.get("NetworkSettings", {}).get("Ports", {}),
                        "ip": ip
                    })
                
                # 获取结果后存入缓存并返回
                if not filters:
                    self._containers_cache[cache_key] = (results, time.time())
                return results
            except Exception as e:
                logger.warning(f"Docker-py client failed, falling back to SSH Shell: {e}")

        # 如果客户端不可用或报错，通过 SSH 执行 docker ps 命令解析 (纯 SSH 模式)
        if self.host_config.get("type") == "ssh" or self.host_config.get("type") == "local":
            cmd = "docker ps -a --format '{{json .}}'" if all else "docker ps --format '{{json .}}'"
            res = self.exec_command(cmd)
            if res["success"]:
                try:
                    import json
                    lines = res["stdout"].strip().split('\n')
                    results = []
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

    def get_containers_stats(self) -> Dict[str, Any]:
        """获取所有容器的实时资源占用"""
        cmd = "docker stats --no-stream --format '{{json .}}'"
        res = self.exec_command(cmd, log_error=False)
        stats = {}
        if res["success"]:
            try:
                import json
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
                    except: continue
            except Exception as e:
                logger.error(f"Failed to parse docker stats: {e}")
        return stats

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
                        except: pass
                        
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
            
            # 操作后清理列表缓存
            cache_keys = [f"{self.host_id}_True", f"{self.host_id}_False"]
            for k in cache_keys:
                if k in self._containers_cache:
                    del self._containers_cache[k]
            
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

    async def get_image_update_info(self, image_tag: str):
        """
        获取镜像的更新信息。支持 Docker Hub 以及第三方仓库 (如 lscr.io, ghcr.io)。
        """
        if not image_tag: return None
        
        # 1. 解析镜像名与仓库地址
        # lscr.io/linuxserver/qbittorrent:latest -> host=lscr.io, repo=linuxserver/qbittorrent, tag=latest
        # nginx -> host=registry-1.docker.io, repo=library/nginx, tag=latest
        parts = image_tag.split("/")
        host = "registry-1.docker.io"
        repo = ""
        tag = "latest"
        
        full_repo_path = image_tag
        if ":" in image_tag:
            full_repo_path, tag = image_tag.rsplit(":", 1)
            
        if "." in parts[0] or ":" in parts[0]:
            host = parts[0]
            repo = "/".join(parts[1:])
            if ":" in repo: repo = repo.rsplit(":", 1)[0]
        else:
            repo = full_repo_path
            if "/" not in repo:
                repo = f"library/{repo}"
        
        # 修正 Docker Hub 的主机名
        reg_host = host
        if host == "docker.io": reg_host = "registry-1.docker.io"
            
        # 2. 获取本地 RepoDigests
        local_digests = []
        res = self.exec_command(f"docker inspect --format='{{{{json .RepoDigests}}}}' {image_tag}", log_error=False)
        if res["success"] and res["stdout"].strip():
            try:
                import json
                local_digests = json.loads(res["stdout"])
            except: pass
            
        if not local_digests and self.client:
            try:
                img = self.client.images.get(image_tag)
                local_digests = img.attrs.get("RepoDigests", [])
            except: pass
            
        # 3. 动态获取远程 Digest (支持 OCI 挑战认证)
        remote_digest = ""
        try:
            from app.utils.http_client import get_async_client
            # 扩展 Accept 头，支持多架构镜像清单
            accept_headers = (
                "application/vnd.docker.distribution.manifest.v2+json, "
                "application/vnd.docker.distribution.manifest.list.v2+json, "
                "application/vnd.oci.image.manifest.v1+json, "
                "application/vnd.oci.image.index.v1+json"
            )
            
            async with get_async_client(timeout=15.0) as client:
                manifest_url = f"https://{reg_host}/v2/{repo}/manifests/{tag}"
                headers = {"Accept": accept_headers}
                
                # 显式开启重定向跟随
                res = await client.get(manifest_url, headers=headers, follow_redirects=True)
                
                if res.status_code == 401:
                    auth_header = res.headers.get("WWW-Authenticate", "")
                    if "Bearer" in auth_header:
                        import re
                        realm = re.search(r'realm="([^"]+)"', auth_header).group(1)
                        service_match = re.search(r'service="([^"]+)"', auth_header)
                        service = service_match.group(1) if service_match else ""
                        scope_match = re.search(r'scope="([^"]+)"', auth_header)
                        scope = scope_match.group(1) if scope_match else f"repository:{repo}:pull"
                        
                        auth_params = {"scope": scope}
                        if service: auth_params["service"] = service
                        
                        auth_res = await client.get(realm, params=auth_params, follow_redirects=True)
                        if auth_res.status_code == 200:
                            token = auth_res.json().get("token") or auth_res.json().get("access_token")
                            headers["Authorization"] = f"Bearer {token}"
                            res = await client.get(manifest_url, headers=headers, follow_redirects=True)
                
                if res.status_code == 200:
                    remote_digest = res.headers.get("Docker-Content-Digest", "")
                else:
                    logger.debug(f"HTTP {res.status_code} for {manifest_url}")
        except Exception as e:
            logger.warning(f"Failed to fetch remote digest for {image_tag} on {host}: {e}")

        # 4. 对比判定
        has_update = False
        if remote_digest:
            is_latest = any(remote_digest in d for d in local_digests)
            has_update = not is_latest
            status_text = "发现新版本" if has_update else "已是最新"
            logger.info(f"🔍 [镜像检测] 站点: {host} | 镜像: {repo}:{tag}")
            logger.info(f"   ┣ 本地指纹: {local_digests}")
            logger.info(f"   ┣ 远程指纹: {remote_digest}")
            logger.info(f"   ┗ 判定结果: {status_text}")
        else:
            logger.warning(f"⚠️ [镜像检测] 无法获取远程指纹: {image_tag} (Host: {host})")

        return {
            "image": image_tag,
            "local_digests": local_digests,
            "remote_digest": remote_digest,
            "has_update": has_update
        }

    @staticmethod
    async def run_auto_update_task():
        """
        极致精准版：根据记录中的 host_id 直接定点更新
        """
        logger.info("🚀 [Docker] 开始执行每日自动更新任务...")
        from app.core.config_manager import get_config
        from app.services.notification_service import NotificationService
        
        config = get_config()
        # 检查是否全局开启了自动更新
        auto_settings = config.get("docker_auto_update_settings", {"enabled": True})
        if not auto_settings.get("enabled"):
            logger.info("ℹ️ [Docker] 自动更新已全局关闭，跳过执行。")
            return

        all_hosts = config.get("docker_hosts", [])
        container_settings = config.get("docker_container_settings", {})
        
        # 1. 筛选出所有开启了自动更新且有 host_id 的记录
        tasks_by_host = {}
        for name, settings in container_settings.items():
            if settings.get("auto_update") and settings.get("host_id"):
                h_id = settings.get("host_id")
                if h_id not in tasks_by_host:
                    tasks_by_host[h_id] = []
                tasks_by_host[h_id].append(name)
        
        if not tasks_by_host:
            logger.info("ℹ️ [Docker] 没有发现待更新的任务记录，任务结束。")
            return

        updated_count = 0
        error_count = 0

        # 2. 定点执行
        for h_id, names in tasks_by_host.items():
            host_config = next((h for h in all_hosts if h.get("id") == h_id), None)
            if not host_config:
                logger.error(f"❌ [Docker] 找不到 ID 为 {h_id} 的主机配置，跳过容器: {names}")
                continue

            host_name = host_config.get("name", "Unknown")
            logger.info(f"🌐 [Docker] 正在连接主机 [{host_name}] 检查容器: {', '.join(names)}")
            
            try:
                from app.services.docker_service import DockerService
                service = DockerService(host_config)
                # 使用 to_thread 异步获取容器列表
                containers = await asyncio.to_thread(service.list_containers, True, {"name": names})
                
                for container in containers:
                    c_name = container.get("name")
                    if c_name in names:
                        image = container.get("image")
                        try:
                            update_info = await service.get_image_update_info(image)
                            if update_info and update_info.get("has_update"):
                                logger.info(f"✨ [Docker][{host_name}] 发现镜像更新: {c_name}")
                                c_id = container.get("full_id") or container.get("id")
                                # 使用 to_thread 异步执行重构操作
                                if await asyncio.to_thread(service.container_action, c_id, "recreate"):
                                    updated_count += 1
                                    await NotificationService.emit(
                                        event="docker.auto_update",
                                        title="Docker 自动更新成功",
                                        message=f"主机: {host_name}\n容器: {c_name}\n镜像: {image}\n结果: 已更新并重构"
                                    )
                                else:
                                    error_count += 1
                        except Exception as e:
                            logger.error(f"❌ [Docker][{host_name}] 处理 {c_name} 异常: {e}")
                            error_count += 1
            except Exception as e:
                logger.error(f"❌ [Docker] 无法连接主机 {host_name}: {e}")
                error_count += len(names)

        logger.info(f"🏁 [Docker] 自动更新完毕。更新: {updated_count}, 失败: {error_count}")

    _scheduler = None
    _is_running = False

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            import os
            import pytz
            tz_name = os.getenv("TZ", "UTC")
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC
            cls._scheduler = AsyncIOScheduler(timezone=tz)
        return cls._scheduler

    @classmethod
    async def start_scheduler(cls):
        if not cls._is_running:
            cls.get_scheduler().start()
            cls._is_running = True
            logger.info("📅 [Docker] 自动更新调度器已启动")
            await cls.reload_scheduler()

    @classmethod
    async def reload_scheduler(cls):
        """重载调度器设置"""
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        from app.core.config_manager import get_config
        import os
        import pytz
        
        scheduler = cls.get_scheduler()
        scheduler.remove_all_jobs()
        
        config = get_config()
        settings = config.get("docker_auto_update_settings", {"enabled": True, "type": "cron", "value": "03:00"})
        
        if not settings.get("enabled"):
            logger.info("📅 [Docker] 自动更新已停用")
            return

        tz_name = os.getenv("TZ", "UTC")
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        try:
            stype = settings.get("type", "cron")
            sval = settings.get("value", "03:00")
            
            if stype == "cron":
                if ":" in sval:
                    h, m = sval.split(":")
                    trigger = CronTrigger(hour=int(h), minute=int(m), timezone=tz)
                else:
                    trigger = CronTrigger.from_crontab(sval, timezone=tz)
            else: # interval (minutes)
                trigger = IntervalTrigger(minutes=int(sval), timezone=tz)

            scheduler.add_job(
                DockerService.run_auto_update_task,
                trigger,
                id="docker_auto_update",
                replace_existing=True
            )
            logger.info(f"📅 [Docker] 自动更新已重载 ({stype}: {sval}, 时区: {tz_name})")
        except Exception as e:
            logger.error(f"❌ [Docker] 重载调度器失败: {e}")

    def test_connection(self) -> bool:
        if not self.client: return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def exec_command(self, command: str, cwd: Optional[str] = None, log_error: bool = True, timeout: int = 60) -> Dict[str, Any]:
        """在远程或本地执行 shell 命令"""
        import subprocess
        full_cmd = f"cd {cwd} && {command}" if cwd else command
        
        # 噪音过滤器：过滤掉那些无害但烦人的 Docker 警告
        noise_filters = [
            "the attribute `version` is obsolete",
            "search/all: the attribute `version` is obsolete",
            "recreate: the attribute `version` is obsolete"
        ]

        def filter_noise(text: str) -> str:
            if not text: return ""
            lines = text.split('\n')
            # 只有当该行不包含任何噪音片段时才保留
            filtered = [line for line in lines if not any(noise in line for noise in noise_filters)]
            return '\n'.join(filtered).strip()

        if self.host_config.get("type") == "local":
            try:
                process = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                stdout = process.stdout
                stderr = filter_noise(process.stderr)
                
                if process.returncode != 0 and log_error:
                    logger.error(f"Local Command Failed: {command} (Code: {process.returncode}, Err: {stderr})")
                return {"success": process.returncode == 0, "stdout": stdout, "stderr": stderr, "timeout": False}
            except subprocess.TimeoutExpired:
                if log_error: logger.warning(f"Local Command Timeout ({timeout}s): {command}")
                return {"success": False, "stdout": "", "stderr": "Command Timeout", "timeout": True}
            except Exception as e:
                return {"success": False, "stdout": "", "stderr": str(e), "timeout": False}
        
        elif self.host_config.get("type") == "ssh":
            ssh = None
            # 尝试从缓存获取
            if self.host_id in self._ssh_clients_cache:
                c, ts = self._ssh_clients_cache[self.host_id]
                # 缩短复用时间到 5 分钟，提高安全性
                if time.time() - ts < 300: 
                    try:
                        transport = c.get_transport()
                        if transport and transport.is_active():
                            # 发送一个轻量级心跳信号检查 Socket 是否真的可用
                            transport.send_ignore()
                            ssh = c
                    except:
                        pass
            
            if not ssh:
                # 清理失效缓存
                if self.host_id in self._ssh_clients_cache:
                    try: self._ssh_clients_cache[self.host_id][0].close()
                    except: pass
                    del self._ssh_clients_cache[self.host_id]

                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    ssh_host = self.host_config.get("ssh_host")
                    ssh_user = self.host_config.get("ssh_user", "root")
                    ssh_port = self.host_config.get("ssh_port", 22)
                    ssh_pass = self.host_config.get("ssh_pass")
                    
                    ssh.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_pass, timeout=10)
                    self._ssh_clients_cache[self.host_id] = (ssh, time.time())
                except Exception as e:
                    if log_error: logger.error(f"SSH Connection Error during exec: {e}")
                    return {"success": False, "stdout": "", "stderr": str(e), "timeout": False}

            try:
                # 增加 exec_command 的超时保护
                stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
                
                out = stdout.read().decode()
                err = filter_noise(stderr.read().decode())
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status != 0 and log_error:
                    logger.error(f"SSH Command Failed: {command} (Code: {exit_status}, Err: {err})")
                
                return {
                    "success": exit_status == 0,
                    "stdout": out,
                    "stderr": err,
                    "timeout": False
                }
            except Exception as e:
                # 检查是否是超时
                is_timeout = "timeout" in str(e).lower()
                # 如果执行失败且是因为连接断开，则清理缓存
                if self.host_id in self._ssh_clients_cache:
                    try: ssh.close()
                    except: pass
                    del self._ssh_clients_cache[self.host_id]
                if log_error: logger.error(f"SSH Exec Error: {e}")
                return {"success": False, "stdout": "", "stderr": str(e), "timeout": is_timeout}
        return {"success": False, "stdout": "", "stderr": "Unsupported host type", "timeout": False}

    def read_file(self, file_path: str) -> str:
        if self.host_config.get("type") == "local":
            if not os.path.exists(file_path): return ""
            with open(file_path, "r") as f: return f.read()
            
        elif self.host_config.get("type") == "ssh":
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(self.host_config.get("ssh_host"), 
                            port=self.host_config.get("ssh_port", 22), 
                            username=self.host_config.get("ssh_user"), 
                            password=self.host_config.get("ssh_pass"),
                            timeout=10)
                sftp = ssh.open_sftp()
                with sftp.open(file_path, 'r') as f:
                    content = f.read().decode()
                sftp.close()
                return content
            except Exception as e:
                logger.error(f"SFTP Read Error: {e}")
                return ""
            finally:
                ssh.close()
        return ""

    def write_file(self, file_path: str, content: str) -> bool:
        if self.host_config.get("type") == "local":
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f: f.write(content)
                return True
            except: return False
            
        elif self.host_config.get("type") == "ssh":
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(self.host_config.get("ssh_host"), 
                            port=self.host_config.get("ssh_port", 22), 
                            username=self.host_config.get("ssh_user"), 
                            password=self.host_config.get("ssh_pass"),
                            timeout=10)
                sftp = ssh.open_sftp()
                remote_dir = os.path.dirname(file_path)
                ssh.exec_command(f"mkdir -p {remote_dir}")
                with sftp.open(file_path, 'w') as f:
                    f.write(content)
                sftp.close()
                return True
            except Exception as e:
                logger.error(f"SFTP Write Error: {e}")
                return False
            finally:
                ssh.close()
        return False

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

    # ==================== 镜像管理 ====================

    _SAFE_REF_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.\-/:@]+$")

    @classmethod
    def _ensure_safe_ref(cls, ref: str) -> str:
        """校验镜像引用/ID 合法性，防止 CLI 兜底时被注入"""
        if not ref or len(ref) > 300 or not cls._SAFE_REF_RE.fullmatch(ref):
            raise Exception(f"非法的镜像引用: {ref}")
        return ref

    @staticmethod
    def _format_size(size_bytes) -> str:
        try:
            size = float(size_bytes or 0)
        except (TypeError, ValueError):
            return "--"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @staticmethod
    def _format_created(created) -> str:
        """将镜像创建时间转为相对时间描述"""
        if not created:
            return "--"
        try:
            import datetime
            if isinstance(created, (int, float)):
                dt = datetime.datetime.utcfromtimestamp(created)
            else:
                dt = datetime.datetime.fromisoformat(str(created).split(".")[0].replace("Z", ""))
            delta = datetime.datetime.utcnow() - dt
            if delta.days > 0: return f"{delta.days} 天前"
            hours, remainder = divmod(delta.seconds, 3600)
            if hours > 0: return f"{hours} 小时前"
            return f"{max(remainder // 60, 1)} 分钟前"
        except Exception:
            return str(created)

    @staticmethod
    def _split_image_tag(ref: str):
        """拆分镜像名与标签（正确处理 registry 带端口的情形）"""
        colon, slash = ref.rfind(":"), ref.rfind("/")
        if colon > slash:
            return ref[:colon], ref[colon + 1:]
        return ref, "latest"

    def _invalidate_images_cache(self):
        self._images_cache.pop(f"{self.host_id}_images", None)

    def _invalidate_client_on_ssh_error(self, e: Exception) -> None:
        """SSH 隧道类错误（如通道耗尽 Connect failed）时丢弃缓存的客户端，下次调用重建连接自愈"""
        text = f"{type(e).__name__}: {e}"
        if "Connect failed" in text or "ChannelException" in text or "SSHException" in text:
            self._clients_cache.pop(self.host_id, None)
            logger.warning(f"[Docker] 检测到 SSH 通道异常，已重置主机 {self.host_id} 的连接缓存")

    def list_images(self) -> List[Dict[str, Any]]:
        """获取镜像列表（含占用状态），SDK 失败时回退 docker images CLI"""
        cache_key = f"{self.host_id}_images"
        if cache_key in self._images_cache:
            data, ts = self._images_cache[cache_key]
            if time.time() - ts < 5:
                return data

        # 容器占用映射：镜像完整ID -> [容器名]
        used_map = {}
        if self.client:
            try:
                for c in self.client.containers.list(all=True):
                    try:
                        used_map.setdefault(c.image.id, []).append(c.name)
                    except Exception:
                        continue
            except Exception as e:
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"[Docker] 获取容器占用信息失败: {e}")

        results = []
        if self.client:
            try:
                for img in self.client.images.list(all=True):
                    tags = img.tags or []
                    used_by = used_map.get(img.id, [])
                    results.append({
                        "id": img.short_id,
                        "full_id": img.id,
                        "tags": tags,
                        "repo_tag": tags[0] if tags else "<none>:<none>",
                        "size": self._format_size(img.attrs.get("Size")),
                        "created": self._format_created(img.attrs.get("Created")),
                        "in_use": bool(used_by),
                        "used_by": used_by,
                        "dangling": not tags,
                    })
                self._images_cache[cache_key] = (results, time.time())
                return results
            except Exception as e:
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py images.list failed, falling back to CLI: {e}")

        # CLI 兜底：docker images -a，占用状态通过 docker ps -a 的镜像名交叉比对
        res = self.exec_command("docker images -a --format '{{json .}}'", log_error=False)
        if res["success"]:
            try:
                cli_used = {}
                ps_res = self.exec_command("docker ps -a --format '{{json .}}'", log_error=False)
                if ps_res["success"]:
                    for line in ps_res["stdout"].strip().split("\n"):
                        if not line: continue
                        try:
                            cc = json.loads(line)
                            cli_used.setdefault(cc.get("Image"), []).append(cc.get("Names"))
                        except Exception: continue

                for line in res["stdout"].strip().split("\n"):
                    if not line: continue
                    try:
                        m = json.loads(line)
                    except Exception: continue
                    repo, tag = m.get("Repository", ""), m.get("Tag", "")
                    ref = f"{repo}:{tag}" if repo and repo != "<none>" else "<none>:<none>"
                    used_by = cli_used.get(ref, []) or cli_used.get(m.get("ID"), [])
                    results.append({
                        "id": (m.get("ID") or "")[:12],
                        "full_id": m.get("ID"),
                        "tags": [ref] if repo and repo != "<none>" else [],
                        "repo_tag": ref,
                        "size": m.get("Size"),
                        "created": m.get("CreatedSince"),
                        "in_use": bool(used_by),
                        "used_by": used_by,
                        "dangling": not repo or repo == "<none>",
                    })
                self._images_cache[cache_key] = (results, time.time())
            except Exception as e:
                logger.error(f"Failed to parse docker images output: {e}")
        return results

    def get_image_info(self, image_id: str) -> Dict[str, Any]:
        """获取镜像 inspect 详情，SDK 失败时回退 docker inspect"""
        self._ensure_safe_ref(image_id)
        if self.client:
            try:
                return self.client.images.get(image_id).attrs
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py inspect failed, falling back to CLI: {e}")
        res = self.exec_command(f"docker inspect {image_id}")
        if res["success"]:
            try:
                data = json.loads(res["stdout"])
                if isinstance(data, list) and data:
                    return data[0]
            except Exception:
                pass
        raise Exception(res.get("stderr") or f"无法获取镜像 {image_id[:12]} 详情")

    def remove_image(self, image_id: str, force: bool = False) -> bool:
        """删除镜像，SDK 失败时回退 docker rmi"""
        self._ensure_safe_ref(image_id)
        if self.client:
            try:
                self.client.images.remove(image_id, force=force)
                self._invalidate_images_cache()
                return True
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                if "image is being used" in str(e) or "conflict" in str(e).lower():
                    raise Exception(f"镜像 {image_id[:12]} 正被容器使用，无法删除（可尝试强制删除）")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py remove failed, falling back to CLI: {e}")
        res = self.exec_command(f"docker rmi {'-f ' if force else ''}{image_id}")
        if res["success"]:
            self._invalidate_images_cache()
            return True
        raise Exception(res.get("stderr") or "docker rmi 执行失败")

    def tag_image(self, image_id: str, repo: str, tag: str = "latest") -> bool:
        """为镜像打标签，SDK 失败时回退 docker tag"""
        self._ensure_safe_ref(image_id)
        self._ensure_safe_ref(f"{repo}:{tag}")
        if self.client:
            try:
                image = self.client.images.get(image_id)
                if image.tag(repo, tag):
                    self._invalidate_images_cache()
                    return True
                raise Exception("打标签失败")
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py tag failed, falling back to CLI: {e}")
        res = self.exec_command(f"docker tag {image_id} {repo}:{tag}")
        if res["success"]:
            self._invalidate_images_cache()
            return True
        raise Exception(res.get("stderr") or "docker tag 执行失败")

    @classmethod
    def register_pull_task(cls, host_id: str, image_ref: str) -> str:
        """登记一个拉取任务并返回 task_id，同时清理 1 小时前的已完成任务"""
        now = time.time()
        for tid in list(cls._pull_tasks.keys()):
            t = cls._pull_tasks[tid]
            if t.get("done") and now - (t.get("finished_at") or now) > 3600:
                del cls._pull_tasks[tid]
        task_id = f"{host_id}_{int(now * 1000)}_{uuid.uuid4().hex[:6]}"
        cls._pull_tasks[task_id] = {
            "host_id": host_id, "image": image_ref, "status": "pending",
            "lines": [], "layers": {}, "done": False, "success": False,
            "error": None, "created_at": now, "finished_at": None,
        }
        return task_id

    @classmethod
    def get_pull_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        return cls._pull_tasks.get(task_id)

    def pull_image(self, task_id: str, image_ref: str) -> None:
        """阻塞执行镜像拉取，进度实时写入 _pull_tasks（由 API 层放入后台线程调用）"""
        task = self._pull_tasks.get(task_id)
        if task is None:
            return
        self._ensure_safe_ref(image_ref)
        task["status"] = "running"
        try:
            if self.client:
                repo, tag = self._split_image_tag(image_ref)
                stream = self.client.api.pull(repo, tag=tag, stream=True, decode=True)
                try:
                    for chunk in stream:
                        err = chunk.get("error")
                        if err:
                            raise Exception(err)
                        layer = chunk.get("id")
                        status = chunk.get("status", "")
                        progress = chunk.get("progress", "")
                        if layer and status in ("Downloading", "Extracting", "Waiting", "Verifying Checksum"):
                            task["layers"][layer] = {"status": status, "progress": progress}
                        elif status.startswith(("Status", "Digest")):
                            task["lines"].append(status)
                        elif status in ("Pull complete", "Already exists", "Download complete"):
                            task["lines"].append(f"{layer or ''} {status}".strip())
                        if len(task["lines"]) > 50:
                            task["lines"] = task["lines"][-50:]
                finally:
                    # 显式关闭流，避免 SSH 隧道通道泄漏
                    try:
                        stream.close()
                    except Exception:
                        pass
                task["success"] = True
                task["status"] = "success"
            else:
                res = self.exec_command(f"docker pull {image_ref}", timeout=1800)
                task["lines"] = [l for l in (res.get("stdout") or "").strip().split("\n") if l][-50:]
                if not res["success"]:
                    raise Exception(res.get("stderr") or "docker pull 执行失败")
                task["success"] = True
                task["status"] = "success"
        except Exception as e:
            self._invalidate_client_on_ssh_error(e)
            task["success"] = False
            task["status"] = "failed"
            task["error"] = str(e)
            logger.error(f"[Docker] 拉取镜像失败 {image_ref}: {e}")
        finally:
            task["done"] = True
            task["finished_at"] = time.time()
            self._invalidate_images_cache()

    @staticmethod
    def _spool_to_temp(fileobj) -> str:
        """将上传的文件流分块落盘为临时文件，返回路径"""
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".tar")
        with os.fdopen(fd, "wb") as tmp:
            while True:
                chunk = fileobj.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        return path

    def export_image(self, image_id: str, output_path: str) -> bool:
        """导出镜像为 tar 文件（docker save）。SSH 主机走独立连接的 CLI+SFTP，避免长时间占用 docker-py 隧道通道"""
        self._ensure_safe_ref(image_id)

        if self.host_config.get("type") == "ssh":
            remote_tmp = f"/tmp/lens_image_export_{int(time.time())}.tar"
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.host_config.get("ssh_host"),
                port=self.host_config.get("ssh_port", 22),
                username=self.host_config.get("ssh_user", "root"),
                password=self.host_config.get("ssh_pass"),
                timeout=15,
            )
            try:
                _, stdout, stderr = ssh.exec_command(f"docker save -o {remote_tmp} {image_id}", timeout=1800)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    err = stderr.read().decode().strip()
                    raise Exception(err or "docker save 执行失败")
                sftp = ssh.open_sftp()
                try:
                    sftp.get(remote_tmp, output_path)
                finally:
                    sftp.close()
                return True
            finally:
                try:
                    ssh.exec_command(f"rm -f {remote_tmp}", timeout=30)
                except Exception:
                    pass
                ssh.close()

        if self.client:
            try:
                image = self.client.images.get(image_id)
                with open(output_path, "wb") as f:
                    for chunk in image.save():
                        f.write(chunk)
                return True
            except Exception as e:
                if "No such image" in str(e):
                    raise Exception(f"镜像 {image_id[:12]} 不存在")
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py save failed, falling back to CLI: {e}")

        # 本地 CLI 兜底
        res = self.exec_command(f"docker save -o {output_path} {image_id}", timeout=1800)
        if res["success"]:
            return True
        raise Exception(res.get("stderr") or "docker save 执行失败")

    @staticmethod
    def _clean_load_result(result) -> List[str]:
        """整理 docker load 的返回流为纯文本行（只保留末尾若干行，最关键的 Loaded image 信息在末尾）"""
        lines = []
        for item in (result or []):
            if isinstance(item, bytes):
                text = item.decode("utf-8", "replace")
            elif isinstance(item, dict):
                text = item.get("stream") or item.get("error") or ""
                if isinstance(text, bytes):
                    text = text.decode("utf-8", "replace")
                if not text:
                    text = json.dumps(item, ensure_ascii=False, default=str)
            else:
                text = str(item)
            text = text.strip()
            if text:
                lines.append(text)
        return lines[-30:]

    def load_image(self, fileobj) -> List[str]:
        """从 tar 文件导入镜像（docker load），SDK 失败时回退 CLI，返回可读的结果文本行"""
        if self.client:
            try:
                try:
                    fileobj.seek(0)
                except Exception:
                    pass
                # 用底层 API 取原始 JSON 流；高层 images.load() 返回 Image 模型对象，拿不到可读文本
                stream = self.client.api.load_image(fileobj)
                try:
                    raw = list(stream)
                finally:
                    # 显式关闭流，避免 SSH 隧道通道泄漏
                    try:
                        stream.close()
                    except Exception:
                        pass
                self._invalidate_images_cache()
                return self._clean_load_result(raw)
            except Exception as e:
                self._invalidate_client_on_ssh_error(e)
                logger.warning(f"Docker-py load failed, falling back to CLI: {e}")
                try:
                    fileobj.seek(0)
                except Exception:
                    pass

        if self.host_config.get("type") == "ssh":
            # SSH 主机：SFTP 上传到远程临时文件后 docker load
            remote_tmp = f"/tmp/lens_image_load_{int(time.time())}.tar"
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.host_config.get("ssh_host"),
                port=self.host_config.get("ssh_port", 22),
                username=self.host_config.get("ssh_user", "root"),
                password=self.host_config.get("ssh_pass"),
                timeout=15,
            )
            try:
                sftp = ssh.open_sftp()
                try:
                    sftp.putfo(fileobj, remote_tmp)
                finally:
                    sftp.close()
            finally:
                ssh.close()
            try:
                res = self.exec_command(f"docker load -i {remote_tmp}", timeout=1800)
                if not res["success"]:
                    raise Exception(res.get("stderr") or "docker load 执行失败")
                return [(res.get("stdout") or "").strip() or "导入完成"]
            finally:
                self.exec_command(f"rm -f {remote_tmp}", log_error=False)

        # 本地 CLI 兜底
        local_tmp = self._spool_to_temp(fileobj)
        try:
            res = self.exec_command(f"docker load -i {local_tmp}", timeout=1800)
            if not res["success"]:
                raise Exception(res.get("stderr") or "docker load 执行失败")
            return [(res.get("stdout") or "").strip() or "导入完成"]
        finally:
            try:
                os.remove(local_tmp)
            except OSError:
                pass
