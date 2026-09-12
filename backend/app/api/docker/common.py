"""Docker API 公共模型与依赖。"""
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import HTTPException

from app.core.config_manager import get_config
from app.services.docker_service import DockerService

class DockerHostConfig(BaseModel):
    id: Optional[str] = None
    name: str
    type: str # 'local', 'ssh', or 'tcp'
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_user: Optional[str] = "root"
    ssh_pass: Optional[str] = None
    use_tls: Optional[bool] = False
    is_local: Optional[bool] = False # 新增：标记为 Lens 宿主机
    base_url: Optional[str] = None
    compose_scan_paths: Optional[str] = "" # 新增：逗号分隔的扫描路径


class ImagePullRequest(BaseModel):
    image: str

class ImageTagRequest(BaseModel):
    repo: str
    tag: str = "latest"


class DaemonUpdate(BaseModel):
    config: Dict[str, Any]
    restart: bool = False


class DockerAutoUpdateSettings(BaseModel):
    enabled: bool
    type: str # 'cron' or 'interval'
    value: str


def get_docker_service(host_id: str):
    config = get_config()
    hosts = config.get("docker_hosts", [])
    host_config = next((h for h in hosts if h.get("id") == host_id), None)
    
    if not host_config:
        if host_id == "local":
            host_config = {"id": "local", "type": "local", "name": "Local Host"}
        else:
            raise HTTPException(status_code=404, detail="Docker host not configured")
    
    return DockerService(host_config)

