"""Docker 服务基座：客户端连接缓存、shell 命令执行、文件读写。"""
import docker
import paramiko
import os
import time
from typing import Dict, Any, Optional

from app.utils.logger import logger

class DockerServiceBase:
    # 类级别缓存：{ host_id: (client, timestamp) }
    _clients_cache = {}   # { host_id: (client, timestamp) }
    _ssh_clients_cache = {}  # { host_id: (ssh_client, timestamp) }

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
                except Exception:
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
                    except Exception:
                        pass
            
            if not ssh:
                # 清理失效缓存
                if self.host_id in self._ssh_clients_cache:
                    try: self._ssh_clients_cache[self.host_id][0].close()
                    except Exception: pass
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
                    except Exception: pass
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
            except Exception: return False
            
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

    def _invalidate_client_on_ssh_error(self, e: Exception) -> None:
        """SSH 隧道类错误（如通道耗尽 Connect failed）时丢弃缓存的客户端，下次调用重建连接自愈"""
        text = f"{type(e).__name__}: {e}"
        if "Connect failed" in text or "ChannelException" in text or "SSHException" in text:
            self._clients_cache.pop(self.host_id, None)
            logger.warning(f"[Docker] 检测到 SSH 通道异常，已重置主机 {self.host_id} 的连接缓存")
