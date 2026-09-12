"""容器设置与自动更新设置。"""
import asyncio

from typing import Dict, Any
from fastapi import APIRouter, Body

from app.core.config_manager import get_config, save_config
from app.services.docker_service import DockerService

from .common import DockerAutoUpdateSettings

router = APIRouter()

@router.get("/container-settings")
async def get_container_settings():
    config = get_config()
    return config.get("docker_container_settings", {})

@router.post("/container-settings/{container_name}")
async def save_container_settings(container_name: str, settings: Dict[str, Any] = Body(...)):
    config = get_config()
    all_settings = config.get("docker_container_settings", {})
    all_settings[container_name] = settings
    config["docker_container_settings"] = all_settings
    save_config(config)
    return {"message": "Settings saved"}


@router.get("/auto-update/settings")
async def get_auto_update_settings():
    config = get_config()
    return config.get("docker_auto_update_settings", {"enabled": True, "type": "cron", "value": "03:00"})

@router.post("/auto-update/settings")
async def save_auto_update_settings(settings: DockerAutoUpdateSettings):
    config = get_config()
    config["docker_auto_update_settings"] = settings.dict()
    save_config(config)
    
    # 异步触发调度器重载
    asyncio.create_task(DockerService.reload_scheduler())
    
    return {"message": "Settings updated and scheduler reloaded"}
