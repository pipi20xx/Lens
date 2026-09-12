"""Docker 主机配置 CRUD。"""
import time
import uuid

from fastapi import APIRouter, HTTPException

from app.core.config_manager import get_config, save_config
from app.utils.logger import audit_log

from .common import DockerHostConfig

router = APIRouter()

@router.get("/hosts")
async def get_hosts():
    config = get_config()
    return config.get("docker_hosts", [])

@router.post("/hosts")
async def add_host(host: DockerHostConfig):
    start_time = time.time()
    config = get_config()
    hosts = config.get("docker_hosts", [])
    
    new_host = host.dict()
    if not new_host.get("id"):
        # 如果是本地主机且没有 ID，我们可以固定为 local
        if new_host.get("type") == "local":
            new_host["id"] = "local"
        else:
            new_host["id"] = str(uuid.uuid4())
    
    # 防止重复添加相同 ID
    if any(h.get("id") == new_host["id"] for h in hosts):
        raise HTTPException(status_code=400, detail="Host ID already exists")

    hosts.append(new_host)
    config["docker_hosts"] = hosts
    save_config(config)
    
    audit_log("Docker Host Added", (time.time() - start_time) * 1000, [f"Name: {new_host['name']}"])
    return new_host

@router.put("/hosts/{host_id}")
async def update_host(host_id: str, host: DockerHostConfig):
    config = get_config()
    hosts = config.get("docker_hosts", [])
    
    for i, h in enumerate(hosts):
        if h.get("id") == host_id:
            updated_host = host.dict()
            updated_host["id"] = host_id
            hosts[i] = updated_host
            config["docker_hosts"] = hosts
            save_config(config)
            return updated_host
            
    raise HTTPException(status_code=404, detail="Host not found")

@router.delete("/hosts/{host_id}")
async def delete_host(host_id: str):
    start_time = time.time()
    config = get_config()
    hosts = config.get("docker_hosts", [])
    
    new_hosts = [h for h in hosts if h.get("id") != host_id]
    
    # 逻辑修正：如果本来就不在列表里（比如被硬编码注入但没在配置里的 local），也返回成功
    if len(new_hosts) == len(hosts) and host_id != "local":
        raise HTTPException(status_code=404, detail="Host not found")
        
    config["docker_hosts"] = new_hosts
    save_config(config)
    
    audit_log("Docker Host Deleted", (time.time() - start_time) * 1000, [f"ID: {host_id}"])
    return {"message": "Host deleted"}

