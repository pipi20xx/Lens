from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os
import shutil
import subprocess
import json
import time
import asyncio
from app.utils.logger import logger, audit_log
from app.core.config_manager import get_config, save_config
from app.services.docker_service import DockerService

router = APIRouter()

COMPOSE_DIR = "data/compose"

class ComposeProject(BaseModel):
    name: str
    content: str

def get_docker_service(host_id: str):
    config = get_config()
    hosts = config.get("docker_hosts", [])
    host_config = next((h for h in hosts if h.get("id") == host_id), None)
    
    if not host_config:
        raise HTTPException(status_code=404, detail="Docker host not configured")
    
    return DockerService(host_config)

@router.get("/{host_id}/ls")
async def list_directory(host_id: str, path: str = "/"):
    """浏览远程或本地主机的目录内容"""
    service = get_docker_service(host_id)
    # 使用 ls -p 参数，文件夹后会跟 /
    cmd = f"ls -p '{path}'"
    res = service.exec_command(cmd, log_error=False)
    
    if not res["success"]:
        if path != "/":
            return await list_directory(host_id, "/")
        raise HTTPException(status_code=500, detail=res["stderr"])

    items = []
    lines = res["stdout"].strip().split('\n')
    for line in lines:
        if not line: continue
        is_dir = line.endswith('/')
        name = line.rstrip('/')
        items.append({
            "name": name,
            "path": os.path.join(path, name),
            "is_dir": is_dir
        })
    
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"current_path": path, "items": items}

@router.get("/{host_id}/projects")
async def list_projects(host_id: str):
    # 1. 检查后端内存缓存 (5秒 TTL)
    if host_id in DockerService._projects_cache:
        data, ts = DockerService._projects_cache[host_id]
        if time.time() - ts < 5:
            return data

    service = get_docker_service(host_id)
    
    # 封装内部逻辑用于线程执行
    def scan_logic():
        projects = []
        managed_paths = set()
        
        # 2. 尝试通过 docker compose ls 探测已运行的项目
        detect_commands = ["docker compose ls --all --format json", "docker-compose ls --all --format json"]
        for cmd in detect_commands:
            res = service.exec_command(cmd, log_error=False)
            if res["success"] and res["stdout"].strip():
                try:
                    detected_projects = json.loads(res["stdout"])
                    for p in detected_projects:
                        name = p.get("Name") or p.get("Project")
                        config_files = p.get("ConfigFiles") or p.get("ConfigPath")
                        if name and config_files:
                            projects.append({
                                "name": name,
                                "path": os.path.dirname(config_files),
                                "config_file": config_files,
                                "type": "detected",
                                "status": p.get("Status")
                            })
                            managed_paths.add(config_files)
                    break
                except Exception: continue

        # 3. 根据用户配置的扫描路径进行深度搜索
        scan_paths_str = service.host_config.get("compose_scan_paths", "")
        if scan_paths_str:
            paths = [p.strip() for p in scan_paths_str.split(",") if p.strip()]
            for base_path in paths:
                # 静默检查路径是否存在
                check_cmd = f"[ -d '{base_path}' ] && echo 'ok'"
                if service.exec_command(check_cmd, log_error=False)["stdout"].strip() != "ok":
                    continue

                find_cmd = f"find {base_path} -maxdepth 4 \( -name 'docker-compose.yml' -o -name 'docker-compose.yaml' \)"
                res = service.exec_command(find_cmd, log_error=False)
                if res["success"] and res["stdout"].strip():
                    found_files = res["stdout"].strip().split("\n")
                    for file_path in found_files:
                        if not file_path or file_path in managed_paths: continue
                        project_dir = os.path.dirname(file_path)
                        projects.append({
                            "name": os.path.basename(project_dir),
                            "path": project_dir,
                            "config_file": file_path,
                            "type": "scanned",
                            "status": "exited"
                        })
                        managed_paths.add(file_path)

        # 4. 本地内置项目
        if service.host_config.get("type") == "local" and os.path.exists(COMPOSE_DIR):
            for d in os.listdir(COMPOSE_DIR):
                path = os.path.join(COMPOSE_DIR, d)
                cfg = os.path.join(path, "docker-compose.yml")
                if os.path.isdir(path) and cfg not in managed_paths:
                    projects.append({"name": d, "path": path, "config_file": cfg, "type": "internal", "status": "unknown"})
        return projects

    # 在线程池中执行重型扫描任务
    projects = await asyncio.to_thread(scan_logic)
    
    # 更新缓存
    DockerService._projects_cache[host_id] = (projects, time.time())
    return projects

@router.get("/{host_id}/projects/{name}")
async def get_project(host_id: str, name: str, path: Optional[str] = None):
    service = get_docker_service(host_id)
    if not path and service.host_config.get("type") == "local":
        path = os.path.join(COMPOSE_DIR, name, "docker-compose.yml")
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    content = service.read_file(path)
    return {"name": name, "content": content, "path": path}

@router.post("/{host_id}/projects")
async def save_project(host_id: str, project: ComposeProject, path: Optional[str] = None):
    service = get_docker_service(host_id)
    if not path:
        if service.host_config.get("type") == "local":
            path = os.path.join(COMPOSE_DIR, project.name, "docker-compose.yml")
        else:
            path = f"/opt/docker-compose/{project.name}/docker-compose.yml"
    if service.write_file(path, project.content):
        # 保存成功后清理缓存
        if host_id in DockerService._projects_cache:
            del DockerService._projects_cache[host_id]
        return {"message": "Saved", "path": path}
    raise HTTPException(status_code=500, detail="Save failed")

@router.post("/{host_id}/projects/{name}/action")
async def project_action(host_id: str, name: str, action: str = Body(..., embed=True), path: Optional[str] = Body(None, embed=True)):
    service = get_docker_service(host_id)
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    
    cmd_map = {
        "up": f"docker compose -f {path} up -d",
        "down": f"docker compose -f {path} down",
        "pull": f"docker compose -f {path} pull",
        "restart": f"docker compose -f {path} restart"
    }
    
    # 为不同操作设置不同的超时时间
    # up 和 pull 操作可能需要拉取镜像，耗时较长
    timeout = 300 if action in ["up", "pull"] else 90
    
    # 在线程池执行
    res = await asyncio.to_thread(service.exec_command, cmd_map[action], os.path.dirname(path), timeout=timeout)
    
    success = res["success"]
    
    # --- 状态回检逻辑 ---
    # 如果执行结果不成功（或者是由于超时导致的“失败”），我们进行二次状态确认
    if not success:
        logger.info(f"🔍 [Compose] 操作 {action} 返回未成功 (超时={res.get('timeout')})，开始回检状态...")
        
        if action == "up":
            # 检查项目中的容器是否已经在运行
            check_cmd = f"docker compose -f {path} ps --format json"
            check_res = await asyncio.to_thread(service.exec_command, check_cmd, os.path.dirname(path), timeout=30)
            if check_res["success"] and check_res["stdout"].strip():
                try:
                    ps_data = json.loads(check_res["stdout"])
                    # 如果是列表且不为空，或者是非空对象
                    if ps_data:
                        # 只要有容器处于 running 状态，我们就认为 up 成功了（即使之前的命令超时）
                        is_running = any(c.get("State") == "running" or c.get("Status") == "running" for c in (ps_data if isinstance(ps_data, list) else [ps_data]))
                        if is_running:
                            logger.info(f"✨ [Compose] 回检发现容器已在运行，判定操作成功")
                            success = True
                except Exception: pass
        
        elif action == "down":
            # 检查项目中的容器是否已全部移除
            check_cmd = f"docker compose -f {path} ps --format json"
            check_res = await asyncio.to_thread(service.exec_command, check_cmd, os.path.dirname(path), timeout=30)
            if check_res["success"]:
                stdout = check_res["stdout"].strip()
                # 如果输出为空或表示没有容器，则认为 down 成功
                if not stdout or stdout == "[]":
                    logger.info(f"✨ [Compose] 回检发现已无运行容器，判定操作成功")
                    success = True
        
        elif action == "pull":
            # pull 操作如果超时，很难简单验证，但通常镜像已经在后台下载中或已完成
            # 如果没有明确报错（只是超时），我们可以暂时认为它在后台继续进行
            if res.get("timeout"):
                logger.info(f"ℹ️ [Compose] Pull 操作超时，但可能仍在后台下载，提示用户稍后刷新")
                # 这种情况下我们仍然返回 False，但可以自定义更友好的错误详情
                res["stderr"] = "操作耗时较长，镜像可能仍在后台下载中，请稍后刷新查看。"

    # 操作后清理缓存
    if host_id in DockerService._projects_cache:
        del DockerService._projects_cache[host_id]
        
    return {"success": success, "stdout": res["stdout"], "stderr": res["stderr"], "timeout": res.get("timeout", False)}

@router.post("/{host_id}/projects/bulk-action")
async def bulk_project_action(host_id: str, action: str = Body(..., embed=True)):
    """批量操作所有项目"""
    projects = await list_projects(host_id)
    results = []
    
    for p in projects:
        path = p.get("config_file") or p.get("path")
        if not path: continue
        
        # 统一处理路径：如果是目录则尝试寻找 yml
        if not path.endswith((".yml", ".yaml")):
            path = os.path.join(path, "docker-compose.yml")

        try:
            service = get_docker_service(host_id)
            cmd_map = {
                "up": f"docker compose -f {path} up -d",
                "down": f"docker compose -f {path} down"
            }
            if action not in cmd_map: continue
            
            res = service.exec_command(cmd_map[action], cwd=os.path.dirname(path))
            results.append({"name": p['name'], "success": res["success"]})
        except Exception as e:
            results.append({"name": p['name'], "success": False, "error": str(e)})
    
    # 批量操作后清理缓存
    if host_id in DockerService._projects_cache:
        del DockerService._projects_cache[host_id]
            
    return {"results": results}

@router.post("/{host_id}/chmod")
async def chmod_path(host_id: str, path: str = Body(..., embed=True), mode: Optional[str] = Body(None, embed=True), 
                     owner: Optional[str] = Body(None, embed=True), group: Optional[str] = Body(None, embed=True), 
                     recursive: bool = Body(False, embed=True), action: Optional[str] = Body(None, embed=True)):
    service = get_docker_service(host_id)
    rec_flag = "-R " if recursive else ""
    
    if action == 'delete':
        if len(path) < 5 or path in ["/", "/root", "/home", "/etc", "/var"]:
            raise HTTPException(status_code=400, detail="Security Limit: Cannot delete system directories")
        service.exec_command(f"rm -rf '{path}'")
        return {"message": "Deleted"}

    if mode:
        service.exec_command(f"chmod {rec_flag}{mode} '{path}'")
    if owner or group:
        target = f"{owner or ''}:{group or ''}".strip(":")
        service.exec_command(f"chown {rec_flag}{target} '{path}'")
    return {"message": "Success"}

@router.delete("/{host_id}/projects/{name}")
async def delete_project(host_id: str, name: str, path: Optional[str] = None, delete_files: bool = False):
    config = get_config()
    hosts = config.get("docker_hosts", [])
    host_match = next((h for h in hosts if h.get("id") == host_id), None)
    service = get_docker_service(host_id)
    
    if delete_files and path:
        project_dir = os.path.dirname(path).rstrip('/')
        if len(project_dir) < 5 or project_dir in ["/", "/root", "/home", "/etc", "/var"]:
            raise HTTPException(status_code=400, detail="Security Limit: Cannot delete system directories")
        
        service.exec_command(f"rm -rf '{project_dir}'")
        
        if host_match and "compose_scan_paths" in host_match:
            paths = [p.strip().rstrip('/') for p in host_match["compose_scan_paths"].split(",") if p.strip()]
            if project_dir in paths:
                paths = [p for p in paths if p != project_dir]
                host_match["compose_scan_paths"] = ",".join(paths)
                save_config(config)

    # 清理缓存
    if host_id in DockerService._projects_cache:
        del DockerService._projects_cache[host_id]

    return {"message": "Removed"}

@router.post("/{host_id}/projects/{name}/create-backup-task")
async def create_project_backup_task(host_id: str, name: str, path: str = Body(..., embed=True)):
    """为 Compose 项目创建备份任务"""
    import uuid
    from app.services.backup_service import BackupService
    
    config = get_config()
    tasks = config.get("backup_tasks", [])
    
    # 确定源路径（项目文件夹）
    src_path = os.path.dirname(path)
    
    # 默认备份目的地：data/backups/remote_compose
    dst_path = os.path.abspath("data/backups/remote_compose")
    if not os.path.exists(dst_path):
        os.makedirs(dst_path, exist_ok=True)
    
    new_task = {
        "id": str(uuid.uuid4())[:8],
        "name": f"Compose: {name}",
        "mode": "7z" if host_id == "local" else "tar", 
        "src_path": src_path,
        "dst_path": dst_path,
        "enabled": True,
        "schedule_type": "cron",
        "schedule_value": "0 3 * * *", # 默认凌晨3点
        "host_id": host_id,
        "ignore_patterns": ["node_modules", ".git", "__pycache__"]
    }
    
    tasks.append(new_task)
    config["backup_tasks"] = tasks
    save_config(config)
    
    await BackupService.reload_tasks()
    return new_task

@router.post("/{host_id}/create-folder-backup")
async def create_folder_backup(host_id: str, path: str = Body(..., embed=True), name: Optional[str] = Body(None, embed=True)):
    """为指定文件夹创建备份任务"""
    import uuid
    from app.services.backup_service import BackupService
    
    config = get_config()
    tasks = config.get("backup_tasks", [])
    
    # path implies the directory to backup
    src_path = path
    folder_name = os.path.basename(path.rstrip('/'))
    task_name = name or f"Folder: {folder_name}"
    
    # 默认备份目的地：data/backups/ssh_folders
    dst_path = os.path.abspath("data/backups/ssh_folders")
    if not os.path.exists(dst_path):
        os.makedirs(dst_path, exist_ok=True)
    
    new_task = {
        "id": str(uuid.uuid4())[:8],
        "name": task_name,
        "mode": "7z" if host_id == "local" else "tar", 
        "src_path": src_path,
        "dst_path": dst_path,
        "enabled": True,
        "schedule_type": "cron",
        "schedule_value": "0 3 * * *", # 默认凌晨3点
        "host_id": host_id,
        "ignore_patterns": ["node_modules", ".git", "__pycache__"]
    }
    
    tasks.append(new_task)
    config["backup_tasks"] = tasks
    save_config(config)
    
    await BackupService.reload_tasks()
    return new_task
