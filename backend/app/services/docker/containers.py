"""容器操作：列表、统计、动作（启停/重构）、日志、终端 socket。"""
import time

from typing import List, Dict, Any

from app.utils.logger import logger

from .base import DockerServiceBase


class ContainerOpsMixin(DockerServiceBase):
    _containers_cache = {}  # { host_id: (data, timestamp) }

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
                            except Exception: pass

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
                    except Exception: continue
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
