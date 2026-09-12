"""镜像相关接口：列表、拉取进度、导入导出、删除、打标签。"""
import os
import asyncio
import time
import uuid

from fastapi import APIRouter, HTTPException, Body, File, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.config_manager import get_config
from app.services.docker_service import DockerService
from app.services.notification_service import NotificationService
from app.utils.logger import logger, audit_log

from .common import get_docker_service, ImagePullRequest, ImageTagRequest

router = APIRouter()

@router.get("/{host_id}/images")
async def list_images(host_id: str):
    """获取镜像列表（含是否被容器占用）"""
    service = get_docker_service(host_id)
    return await asyncio.to_thread(service.list_images)

@router.post("/{host_id}/images/pull")
async def pull_image(host_id: str, req: ImagePullRequest):
    """后台拉取镜像，通过 /images/pull/{task_id} 轮询进度"""
    image_ref = req.image.strip()
    try:
        DockerService._ensure_safe_ref(image_ref)
    except Exception:
        raise HTTPException(status_code=400, detail="非法的镜像名称")
    task_id = DockerService.register_pull_task(host_id, image_ref)

    async def run_pull_task():
        try:
            audit_log("Docker Image Pull", 0, [f"Host: {host_id}", f"Image: {image_ref}"])
            service = get_docker_service(host_id)
            await asyncio.to_thread(service.pull_image, task_id, image_ref)
            task = DockerService.get_pull_task(task_id) or {}
            config = get_config()
            hosts = config.get("docker_hosts", [])
            host_name = next((h.get("name") for h in hosts if h.get("id") == host_id), host_id)
            await NotificationService.emit(
                event="docker.image_pull",
                title="Docker 镜像拉取结果",
                message=(
                    f"主机: {host_name}\n镜像: {image_ref}\n结果: {'成功' if task.get('success') else '失败'}"
                    + (f"\n错误: {task.get('error')}" if task.get("error") else "")
                )
            )
        except Exception as e:
            logger.error(f"🚨 [Docker] 镜像拉取任务崩溃: {e}")

    asyncio.create_task(run_pull_task())
    logger.info(f"📥 [Docker] 镜像拉取任务已启动: {image_ref} (Host: {host_id}, Task: {task_id})")
    return {"message": f"镜像 {image_ref} 拉取任务已在后台启动", "task_id": task_id, "async": True}

@router.get("/{host_id}/images/pull/{task_id}")
async def get_pull_progress(host_id: str, task_id: str):
    """轮询镜像拉取进度"""
    task = DockerService.get_pull_task(task_id)
    if not task or task.get("host_id") != host_id:
        raise HTTPException(status_code=404, detail="拉取任务不存在")
    return task

@router.get("/{host_id}/images/{image_id}/export")
async def export_image(host_id: str, image_id: str):
    """导出镜像为 tar 文件（docker save）"""
    start_time = time.time()
    logger.info(f"📦 [Docker] 收到镜像导出请求: {image_id} (Host: {host_id})")
    service = get_docker_service(host_id)
    try:
        info = await asyncio.to_thread(service.get_image_info, image_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    tags = info.get("RepoTags") or []
    base = tags[0].replace("/", "_").replace(":", "_") if tags else image_id.replace("sha256:", "")[:12]
    export_dir = "data/tmp/exports"
    os.makedirs(export_dir, exist_ok=True)
    output_path = os.path.join(export_dir, f"export_{uuid.uuid4().hex}.tar")
    try:
        await asyncio.to_thread(service.export_image, image_id, output_path)
    except Exception as e:
        try: os.remove(output_path)
        except OSError: pass
        raise HTTPException(status_code=500, detail=str(e))
    audit_log("Docker Image Export", (time.time() - start_time) * 1000,
              [f"Host: {host_id}", f"Image: {image_id}"])
    # 响应发送完毕后自动清理临时文件
    return FileResponse(output_path, filename=f"{base}.tar", media_type="application/x-tar",
                        background=BackgroundTask(os.remove, output_path))

@router.post("/{host_id}/images/load")
async def load_image(host_id: str, file: UploadFile = File(...)):
    """从 tar 文件导入镜像（docker load）"""
    start_time = time.time()
    filename = file.filename or ""
    if not (filename.endswith(".tar") or filename.endswith(".tar.gz") or filename.endswith(".tgz")):
        raise HTTPException(status_code=400, detail="仅支持 .tar / .tar.gz / .tgz 镜像文件")
    service = get_docker_service(host_id)
    try:
        result = await asyncio.to_thread(service.load_image, file.file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    audit_log("Docker Image Load", (time.time() - start_time) * 1000,
              [f"Host: {host_id}", f"File: {filename}"])
    logger.info(f"📥 [Docker] 镜像导入完成: {filename} (Host: {host_id})")
    return {"message": f"镜像导入完成（{filename}）", "result": result}

@router.get("/{host_id}/images/{image_id}")
async def get_image_detail(host_id: str, image_id: str):
    """获取镜像 inspect 详情"""
    service = get_docker_service(host_id)
    try:
        return await asyncio.to_thread(service.get_image_info, image_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/images/{image_id}/remove")
async def remove_image(host_id: str, image_id: str, force: bool = Body(False, embed=True)):
    """删除镜像"""
    start_time = time.time()
    logger.info(f"🗑️ [Docker] 收到镜像删除请求: {image_id} (Host: {host_id}, force={force})")
    service = get_docker_service(host_id)
    try:
        await asyncio.to_thread(service.remove_image, image_id, force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    audit_log("Docker Image Remove", (time.time() - start_time) * 1000,
              [f"Host: {host_id}", f"Image: {image_id}", f"Force: {force}"])
    return {"message": "镜像已删除"}

@router.post("/{host_id}/images/{image_id}/tag")
async def tag_image(host_id: str, image_id: str, req: ImageTagRequest):
    """为镜像打标签"""
    service = get_docker_service(host_id)
    repo, tag = req.repo.strip(), req.tag.strip() or "latest"
    try:
        await asyncio.to_thread(service.tag_image, image_id, repo, tag)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    audit_log("Docker Image Tag", 0, [f"Host: {host_id}", f"Image: {image_id}", f"Target: {repo}:{tag}"])
    return {"message": f"已为镜像打标签 {repo}:{tag}"}

