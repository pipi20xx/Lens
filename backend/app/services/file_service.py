import os
import shutil
import asyncio
import paramiko
from typing import List, Dict, Any, Optional
from app.utils.logger import logger

class FileService:
    def __init__(self):
        self.mode = 'local' # local or ssh
        self.ssh_client = None

    async def connect_ssh(self, host_info: dict):
        """连接远程 SSH 用于 SFTP 操作"""
        self.mode = 'ssh'
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            pkey = None
            if host_info.get('auth_type') == 'key' and host_info.get('private_key'):
                from io import StringIO
                pkey = paramiko.RSAKey.from_private_key(
                    StringIO(host_info['private_key']),
                    password=host_info.get('private_key_password')
                )

            await asyncio.to_thread(
                self.ssh_client.connect,
                hostname=host_info['host'],
                port=int(host_info.get('port', 22)),
                username=host_info.get('username', 'root'),
                password=host_info.get('password'),
                pkey=pkey,
                timeout=10
            )
            return True
        except Exception as e:
            logger.error(f"[FileService] SSH connection failed: {e}")
            self.close()
            raise e

    def close(self):
        if self.ssh_client:
            try: self.ssh_client.close()
            except Exception: pass

    async def list_dir(self, path="/"):
        if self.mode == 'local':
            return await asyncio.to_thread(self._local_list_dir, path)
        else:
            return await asyncio.to_thread(self._sftp_list_dir, path)

    def _local_list_dir(self, path):
        items = []
        try:
            for entry in os.scandir(path):
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "mode": oct(stat.st_mode)[-4:]
                })
        except Exception as e:
            raise e
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return items

    def _sftp_list_dir(self, path):
        sftp = self.ssh_client.open_sftp()
        try:
            items = []
            for attr in sftp.listdir_attr(path):
                import stat
                is_dir = stat.S_ISDIR(attr.st_mode)
                items.append({
                    "name": attr.filename,
                    "path": os.path.join(path, attr.filename).replace("\\", "/"),
                    "is_dir": is_dir,
                    "size": attr.st_size,
                    "mtime": attr.st_mtime,
                    "mode": oct(attr.st_mode)[-4:]
                })
            items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            return items
        finally:
            sftp.close()

    async def read_file(self, path):
        if self.mode == 'local':
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            return await asyncio.to_thread(self._sftp_read, path)

    def _sftp_read(self, path):
        sftp = self.ssh_client.open_sftp()
        try:
            with sftp.open(path, 'r') as f:
                return f.read().decode('utf-8', errors='ignore')
        finally:
            sftp.close()

    async def write_file(self, path, content):
        if self.mode == 'local':
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        else:
            return await asyncio.to_thread(self._sftp_write, path, content)

    def _sftp_write(self, path, content):
        sftp = self.ssh_client.open_sftp()
        try:
            parent = os.path.dirname(path).replace("\\", "/")
            try:
                sftp.stat(parent)
            except IOError:
                self.ssh_client.exec_command(f"mkdir -p '{parent}'")
            
            with sftp.open(path, 'w') as f:
                f.write(content)
            return True
        finally:
            sftp.close()

    async def upload_file(self, path: str, file_obj):
        """上传二进制文件"""
        if self.mode == 'local':
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                # 假设 file_obj 是一个具有 read 方法的文件类对象
                while chunk := await file_obj.read(1024 * 1024): # 1MB chunks
                    f.write(chunk)
            return True
        else:
            return await asyncio.to_thread(self._sftp_upload, path, file_obj)

    def _sftp_upload(self, path, file_obj):
        sftp = self.ssh_client.open_sftp()
        try:
            parent = os.path.dirname(path).replace("\\", "/")
            try:
                sftp.stat(parent)
            except IOError:
                self.ssh_client.exec_command(f"mkdir -p '{parent}'")
            
            with sftp.file(path, 'wb') as f:
                # 同步读取并写入
                while chunk := file_obj.file.read(1024 * 1024):
                    f.write(chunk)
            return True
        finally:
            sftp.close()

    async def download_file(self, path: str):
        """下载二进制文件 (返回文件路径或生成器)"""
        if self.mode == 'local':
            if not os.path.exists(path):
                raise FileNotFoundError("File not found")
            return path
        else:
            # 对于 SSH，我们需要先拉取到本地临时目录，或者使用流式传输
            # 这里为了简单，先返回一个本地临时路径
            return await asyncio.to_thread(self._sftp_download_temp, path)

    def _sftp_download_temp(self, path):
        import tempfile
        sftp = self.ssh_client.open_sftp()
        try:
            # 创建临时文件
            suffix = os.path.splitext(path)[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_path = tmp.name
            tmp.close()
            
            sftp.get(path, tmp_path)
            return tmp_path
        finally:
            sftp.close()

    async def file_action(self, action, path, target=None):
        logger.info(f"[FileService] Action: {action}, Path: {path}, Target: {target}")
        if self.mode == 'local':
            if action == 'delete':
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
            elif action == 'rename' or action == 'move':
                os.rename(path, target)
            elif action == 'mkdir':
                os.makedirs(path, exist_ok=True)
            elif action == 'copy':
                if os.path.isdir(path): shutil.copytree(path, target)
                else: shutil.copy2(path, target)
            return True
        else:
            return await asyncio.to_thread(self._sftp_action, action, path, target)

    def _sftp_action(self, action, path, target):
        sftp = self.ssh_client.open_sftp()
        try:
            cmd = ""
            if action == 'delete':
                cmd = f"rm -rf '{path}'"
            elif action == 'rename' or action == 'move':
                cmd = f"mv '{path}' '{target}'"
            elif action == 'mkdir':
                cmd = f"mkdir -p '{path}'"
            elif action == 'copy':
                cmd = f"cp -r '{path}' '{target}'"
            
            if cmd:
                stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    err_msg = stderr.read().decode().strip()
                    raise Exception(f"Action {action} failed: {err_msg}")
            return True
        finally:
            sftp.close()
