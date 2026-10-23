"""Docker 服务基座：客户端连接缓存、shell 命令执行、文件读写。

性能约定（重要）：
- ``client`` 是**懒加载**属性。只用 ``exec_command`` / ``read_file`` 的接口不会被拖去
  建一条 docker-py 的 SSH 连接并 ping 一次。
- 连接存活检查是**节流**的（``PING_MIN_INTERVAL``），不再每个请求一次往返。
- 所有缓存都是**滑动过期**：只要还在用就不重建。
- ``exec_command`` 故意**不做自动重试**：它承载 ``docker compose up`` / ``rm -rf`` /
  ``systemctl restart`` 这类非幂等命令，重试可能造成重复执行。失败只丢弃缓存连接，
  让下一次调用重建。
"""
import docker
import paramiko
import os
import shlex
import threading
import time
from typing import Dict, Any, Optional

from app.utils.logger import logger

# 连接空闲多久后重建（秒）。滑动过期：还在用就不重建。
CLIENT_IDLE_TTL = 1800
SSH_IDLE_TTL = 1800
# 同一主机最快多久允许 ping 一次，避免"每个请求一次往返"
PING_MIN_INTERVAL = 60


class DockerServiceBase:
    # { host_id: {"client": c, "created": ts, "verified": ts, "used": ts} }
    _clients_cache = {}
    # { host_id: {"client": ssh, "created": ts, "used": ts} }
    _ssh_clients_cache = {}
    # 每主机一把锁，避免并发请求同时重建连接（"全部刷新"会一次打 5 个面板）
    _host_locks = {}
    _host_locks_guard = threading.Lock()

    def __init__(self, host_config: Dict[str, Any]):
        self.host_config = host_config
        self.host_id = host_config.get("id", "local")
        self._client = None
        self._client_tried = False

    # ------------------------------------------------------------------ 锁
    @classmethod
    def _host_lock(cls, host_id: str) -> threading.Lock:
        with cls._host_locks_guard:
            lock = cls._host_locks.get(host_id)
            if lock is None:
                lock = threading.Lock()
                cls._host_locks[host_id] = lock
            return lock

    # ------------------------------------------------------- docker-py 客户端
    @property
    def client(self):
        """懒加载 docker-py 客户端。未成功建立时返回 None（调用方自行走 CLI 兜底）。"""
        if self._client is None and not self._client_tried:
            self._client_tried = True
            self._client = self._get_client()
        return self._client

    def _get_client(self):
        now = time.time()
        entry = self._clients_cache.get(self.host_id)
        if entry:
            if now - entry.get("used", entry["created"]) < CLIENT_IDLE_TTL:
                # 刚验证过就直接复用，省掉一次往返
                if now - entry.get("verified", 0) < PING_MIN_INTERVAL:
                    entry["used"] = now
                    return entry["client"]
                try:
                    entry["client"].ping()
                    entry["verified"] = now
                    entry["used"] = now
                    return entry["client"]
                except Exception:
                    pass
            # 空闲过期或 ping 失败：先关掉旧连接再重建，避免泄漏
            self._close_client()
        return self._build_client()

    def _build_client(self):
        with self._host_lock(self.host_id):
            now = time.time()
            entry = self._clients_cache.get(self.host_id)
            if entry and now - entry.get("verified", 0) < PING_MIN_INTERVAL:
                # 别的线程刚建好，直接复用
                entry["used"] = now
                return entry["client"]

            try:
                client = None
                host_type = self.host_config.get("type", "local")
                if host_type == "local":
                    client = docker.from_env()

                elif host_type == "ssh":
                    ssh_host = self.host_config.get("ssh_host")
                    ssh_user = self.host_config.get("ssh_user", "root")
                    ssh_port = self.host_config.get("ssh_port", 22)
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
                    self._clients_cache[self.host_id] = {
                        "client": client,
                        "created": now,
                        "verified": now,
                        "used": now,
                    }
                    return client

                return None
            except Exception as e:
                logger.error(f"Failed to connect to Docker host {self.host_config.get('name')}: {e}")
                return None

    def _close_client(self):
        entry = self._clients_cache.pop(self.host_id, None)
        if not entry:
            return
        try:
            entry["client"].close()
        except Exception:
            pass

    def test_connection(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------ SSH 连接
    def _ssh_connect_kwargs(self) -> Dict[str, Any]:
        return {
            "hostname": self.host_config.get("ssh_host"),
            "port": self.host_config.get("ssh_port", 22),
            "username": self.host_config.get("ssh_user", "root"),
            "password": self.host_config.get("ssh_pass"),
            "timeout": 10,
        }

    def _close_ssh_client(self):
        entry = self._ssh_clients_cache.pop(self.host_id, None)
        if not entry:
            return
        try:
            entry["client"].close()
        except Exception:
            pass

    def _get_ssh_client(self, log_error: bool = True):
        """取一条可复用的 paramiko 连接（exec_command / read_file / write_file 共用）。

        复用能省掉完整的 TCP + 密钥交换 + 认证；SFTP 也在同一条 transport 上开，
        不再像以前那样每次读写文件都重新握手。
        """
        now = time.time()
        entry = self._ssh_clients_cache.get(self.host_id)
        if entry and now - entry.get("used", entry["created"]) < SSH_IDLE_TTL:
            try:
                transport = entry["client"].get_transport()
                if transport and transport.is_active():
                    transport.send_ignore()  # 轻量心跳，确认 socket 真的还活着
                    entry["used"] = now
                    return entry["client"]
            except Exception:
                pass
            self._close_ssh_client()

        with self._host_lock(f"{self.host_id}:ssh"):
            now = time.time()
            entry = self._ssh_clients_cache.get(self.host_id)
            if entry and now - entry.get("used", entry["created"]) < SSH_IDLE_TTL:
                try:
                    transport = entry["client"].get_transport()
                    if transport and transport.is_active():
                        entry["used"] = now
                        return entry["client"]
                except Exception:
                    pass

            # 走到这里说明：没有缓存、已空闲过期、或 transport 已经不可用。
            # 先收掉旧连接再建新的，避免泄漏。
            self._close_ssh_client()

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(**self._ssh_connect_kwargs())
            except Exception as e:
                if log_error:
                    logger.error(f"SSH Connection Error: {e}")
                return None

            self._ssh_clients_cache[self.host_id] = {"client": ssh, "created": now, "used": now}
            return ssh

    # ------------------------------------------------------------- 命令执行
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
            ssh = self._get_ssh_client(log_error=log_error)
            if not ssh:
                return {"success": False, "stdout": "", "stderr": "SSH connection failed", "timeout": False}

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
                # 执行失败说明这条连接（多半是通道）已经不可用，丢弃缓存让下次重建。
                # 注意：这里不自动重试，见模块 docstring。
                self._close_ssh_client()
                if log_error: logger.error(f"SSH Exec Error: {e}")
                return {"success": False, "stdout": "", "stderr": str(e), "timeout": is_timeout}

        return {"success": False, "stdout": "", "stderr": "Unsupported host type", "timeout": False}

    # --------------------------------------------------------------- 文件
    def read_file(self, file_path: str) -> str:
        if self.host_config.get("type") == "local":
            if not os.path.exists(file_path): return ""
            with open(file_path, "r") as f: return f.read()

        elif self.host_config.get("type") == "ssh":
            ssh = self._get_ssh_client()
            if not ssh:
                return ""
            sftp = None
            try:
                sftp = ssh.open_sftp()
                with sftp.open(file_path, 'r') as f:
                    return f.read().decode()
            except Exception as e:
                logger.error(f"SFTP Read Error: {e}")
                self._close_ssh_client()
                return ""
            finally:
                if sftp:
                    try: sftp.close()
                    except Exception: pass
        return ""

    def write_file(self, file_path: str, content: str) -> bool:
        if self.host_config.get("type") == "local":
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f: f.write(content)
                return True
            except Exception: return False

        elif self.host_config.get("type") == "ssh":
            ssh = self._get_ssh_client()
            if not ssh:
                return False
            sftp = None
            try:
                remote_dir = os.path.dirname(file_path)
                if remote_dir:
                    # 等 mkdir 真正结束，避免和下面的 sftp.open 抢时序
                    _, mk_out, _ = ssh.exec_command(f"mkdir -p {shlex.quote(remote_dir)}")
                    mk_out.channel.recv_exit_status()

                sftp = ssh.open_sftp()
                with sftp.open(file_path, 'w') as f:
                    f.write(content)
                return True
            except Exception as e:
                logger.error(f"SFTP Write Error: {e}")
                self._close_ssh_client()
                return False
            finally:
                if sftp:
                    try: sftp.close()
                    except Exception: pass
        return False

    def _invalidate_client_on_ssh_error(self, e: Exception) -> None:
        """SSH 隧道类错误（如通道耗尽 Connect failed）时丢弃缓存的客户端，下次调用重建连接自愈"""
        text = f"{type(e).__name__}: {e}"
        if "Connect failed" in text or "ChannelException" in text or "SSHException" in text:
            self._close_client()
            logger.warning(f"[Docker] 检测到 SSH 通道异常，已重置主机 {self.host_id} 的连接缓存")
