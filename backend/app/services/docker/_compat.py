"""paramiko 深度补丁：解决 docker-py SSH 隧道的 known_hosts 与密码支持问题。

import 本模块即生效（副作用导入）。
"""
import paramiko

from app.core.config_manager import get_config

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
