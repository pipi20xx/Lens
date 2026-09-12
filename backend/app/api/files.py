from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import os
import re
import shlex
import shutil
import subprocess
from app.db.session import get_db
from app.models.terminal import TerminalHost
from app.services.file_service import FileService
from app.utils.logger import logger

from app.core.config_manager import get_config

router = APIRouter()

async def get_file_service_for_host(host_id: str, db: AsyncSession):
    file_service = FileService()
    
    # 转换判断
    try:
        # 如果是数字，走原有的 TerminalHost 逻辑
        if str(host_id).isdigit():
            h_id = int(host_id)
            if h_id == 0:
                file_service.mode = 'local'
                return file_service
            
            result = await db.execute(select(TerminalHost).where(TerminalHost.id == h_id))
            host_info = result.scalar_one_or_none()
            if not host_info:
                raise HTTPException(status_code=404, detail="Host not found in Terminal registry")
            
            h_dict = {
                "host": host_info.host,
                "port": host_info.port,
                "username": host_info.username,
                "auth_type": host_info.auth_type,
                "password": host_info.password,
                "private_key": host_info.private_key
            }
        else:
            # 否则去 Docker 配置里找
            config = get_config()
            docker_hosts = config.get("docker_hosts", [])
            docker_host = next((h for h in docker_hosts if h.get("id") == host_id), None)
            
            if not docker_host:
                if host_id == "local":
                    file_service.mode = 'local'
                    return file_service
                raise HTTPException(status_code=404, detail=f"Docker host {host_id} not found")
            
            if docker_host.get("type") == "local":
                file_service.mode = 'local'
                return file_service
            
            if docker_host.get("type") != "ssh":
                raise HTTPException(status_code=400, detail="Only SSH-based Docker hosts support file management")
            
            h_dict = {
                "host": docker_host.get("ssh_host"),
                "port": docker_host.get("ssh_port", 22),
                "username": docker_host.get("ssh_user", "root"),
                "auth_type": "password" if docker_host.get("ssh_pass") else "none", # 默认密码模式，除非有私钥
                "password": docker_host.get("ssh_pass"),
                "private_key": None # Docker 配置暂不支持私钥
            }
            # 如果配置里显式写了 auth_type 也可以支持
            if "ssh_key" in docker_host:
                h_dict["auth_type"] = "key"
                h_dict["private_key"] = docker_host["ssh_key"]

        await file_service.connect_ssh(h_dict)
        return file_service
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{host_id}/upload")
async def file_upload(
    host_id: str,
    path: str = Form(...),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    file_service = await get_file_service_for_host(host_id, db)
    try:
        for file in files:
            target_path = os.path.join(path, file.filename).replace("\\", "/")
            await file_service.upload_file(target_path, file)
        return {"status": "success", "count": len(files)}
    finally:
        file_service.close()

@router.get("/{host_id}/download")
async def file_download(
    host_id: str,
    path: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    file_service = await get_file_service_for_host(host_id, db)
    try:
        result = await file_service.download_file(path)
        if file_service.mode == 'ssh':
            background_tasks.add_task(os.remove, result)
            
        return FileResponse(
            path=result,
            filename=os.path.basename(path),
            media_type='application/octet-stream'
        )
    except Exception as e:
        if file_service: file_service.close()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file_service.close()

@router.get("/{host_id}/ls")
async def file_ls(host_id: str, path: str = "/", db: AsyncSession = Depends(get_db)):
    file_service = await get_file_service_for_host(host_id, db)
    try:
        items = await file_service.list_dir(path)
        return {"current_path": path, "items": items}
    finally:
        file_service.close()

@router.get("/{host_id}/read")
async def file_read(host_id: str, path: str, db: AsyncSession = Depends(get_db)):
    file_service = await get_file_service_for_host(host_id, db)
    try:
        content = await file_service.read_file(path)
        return {"content": content}
    finally:
        file_service.close()

@router.post("/{host_id}/write")
async def file_write(
    host_id: str, 
    path: str = Body(..., embed=True), 
    content: str = Body(..., embed=True), 
    db: AsyncSession = Depends(get_db)
):
    file_service = await get_file_service_for_host(host_id, db)
    try:
        await file_service.write_file(path, content)
        return {"status": "success"}
    finally:
        file_service.close()

@router.post("/{host_id}/action")
async def file_action(
    host_id: str, 
    action: str = Body(..., embed=True), 
    path: str = Body(..., embed=True), 
    target: str = Body(None, embed=True),
    db: AsyncSession = Depends(get_db)
):
    file_service = await get_file_service_for_host(host_id, db)
    try:
        await file_service.file_action(action, path, target)
        return {"status": "success"}
    finally:
        file_service.close()

_MODE_RE = re.compile(r"^[0-7]{3,4}$")
_OWNER_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$")

def _run_priv_cmd(file_service: FileService, argv: list):
    """执行 chmod/chown：本地走参数列表（不经 shell），远程对每个参数做 shlex.quote"""
    if file_service.mode == 'local':
        subprocess.run(argv, check=False)
    else:
        cmd = " ".join(shlex.quote(a) for a in argv)
        file_service.ssh_client.exec_command(cmd)

@router.post("/{host_id}/chmod")
async def file_chmod(
    host_id: str,
    path: str = Body(..., embed=True),
    mode: str = Body(None, embed=True),
    owner: str = Body(None, embed=True),
    group: str = Body(None, embed=True),
    recursive: bool = Body(False, embed=True),
    db: AsyncSession = Depends(get_db)
):
    if mode and not _MODE_RE.match(mode):
        raise HTTPException(status_code=400, detail="无效的权限格式（应为 3-4 位八进制，如 755）")
    for name in (owner, group):
        if name and not _OWNER_RE.match(name):
            raise HTTPException(status_code=400, detail=f"无效的用户/组名: {name}")

    file_service = await get_file_service_for_host(host_id, db)
    try:
        if mode:
            argv = ["chmod"] + (["-R"] if recursive else []) + [mode, path]
            _run_priv_cmd(file_service, argv)

        if owner or group:
            target = f"{owner or ''}:{group or ''}".strip(":")
            argv = ["chown"] + (["-R"] if recursive else []) + [target, path]
            _run_priv_cmd(file_service, argv)

        return {"status": "success"}
    finally:
        file_service.close()