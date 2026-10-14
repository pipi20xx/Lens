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

# 合并扫描脚本的分节标记（见 _scan_projects）
_SCAN_SEC_JSON = "@@LENS_COMPOSE_LS@@"
_SCAN_SEC_FIND = "@@LENS_COMPOSE_FIND@@"
_SCAN_SEC_FILES = "@@LENS_COMPOSE_FILES@@"

# 项目列表缓存 TTL（秒）。扫描本身要跑一次远端 exec，5 秒太短了。
PROJECTS_CACHE_TTL = 60

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

def _shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"

@router.get("/{host_id}/ls")
async def list_directory(host_id: str, path: str = "/"):
    """浏览远程或本地主机的目录内容"""
    service = get_docker_service(host_id)
    # 使用 ls -p 参数，文件夹后会跟 /
    cmd = f"ls -p {_shell_quote(path)}"
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

def _registry_entries(config: Dict[str, Any], host_id: str) -> List[Dict[str, Any]]:
    return config.get("compose_registry", {}).get(host_id, []) or []

def _scan_projects(service: DockerService, host_id: str) -> List[Dict[str, Any]]:
    projects = []
    managed_files = set()

    config = get_config()
    remembered_entries = _registry_entries(config, host_id)
    scan_paths = [p.strip().rstrip("/") for p in (service.host_config.get("compose_scan_paths") or "").split(",") if p.strip()]
    remembered_files = [e.get("config_file") for e in remembered_entries if e.get("config_file")]

    # 0. 把"探测项目 + 扫描路径 + 校验记忆文件"合并成**一次** exec。
    #    改前是串行的：1 次 compose ls + 每个扫描路径 2 次（[ -d ] + find）+ 1 次校验，
    #    3 个路径就是 8 次往返。
    script_parts = [
        f"echo '{_SCAN_SEC_JSON}'",
        "docker compose ls --all --format json 2>/dev/null || docker-compose ls --all --format json 2>/dev/null",
        f"echo '{_SCAN_SEC_FIND}'",
    ]
    if scan_paths:
        quoted_paths = " ".join(_shell_quote(p) for p in scan_paths)
        script_parts.append(
            f"for p in {quoted_paths}; do [ -d \"$p\" ] && "
            "find \"$p\" -maxdepth 4 \\( -name 'docker-compose.yml' -o -name 'docker-compose.yaml' "
            "-o -name 'compose.yml' -o -name 'compose.yaml' \\) 2>/dev/null; done"
        )
    script_parts.append(f"echo '{_SCAN_SEC_FILES}'")
    if remembered_files:
        quoted_files = " ".join(_shell_quote(f) for f in remembered_files)
        script_parts.append(f"for f in {quoted_files}; do [ -f \"$f\" ] && echo \"$f\"; done")
    # 结尾 true：保证即使 docker compose 不存在也返回 0，让下面的解析按"空结果"处理
    script_parts.append("true")

    res = service.exec_command("\n".join(script_parts), log_error=False)

    section = None
    markers_seen = set()
    json_lines, found_files, alive_files = [], [], []
    for line in (res.get("stdout") or "").splitlines():
        stripped = line.strip()
        if stripped in (_SCAN_SEC_JSON, _SCAN_SEC_FIND, _SCAN_SEC_FILES):
            section = stripped
            markers_seen.add(stripped)
            continue
        if not stripped:
            continue
        if section == _SCAN_SEC_JSON:
            json_lines.append(line)
        elif section == _SCAN_SEC_FIND:
            found_files.append(stripped)
        elif section == _SCAN_SEC_FILES:
            alive_files.append(stripped)

    if not markers_seen:
        logger.warning(f"[Compose] 扫描脚本无输出，主机 {host_id} 可能不可达: {res.get('stderr')}")
    if not res.get("success"):
        logger.warning(f"[Compose] 扫描脚本执行失败: {res.get('stderr')}")

    # 1. 解析 docker compose ls 的结果。
    #    注意：该命令依据容器上的 label 识别项目，一旦容器被删除（或更新失败导致容器被清掉），
    #    项目会从此输出中消失，因此必须配合下面的扫描路径搜索与持久记忆兜底。
    detected_projects = []
    if json_lines:
        json_text = "\n".join(
            ln for ln in json_lines
            if "obsolete" not in ln and not ln.strip().startswith("WARN")
        )
        try:
            detected_projects = json.loads(json_text)
            if isinstance(detected_projects, dict):
                detected_projects = detected_projects.get("projects") or []
            if not isinstance(detected_projects, list):
                detected_projects = []
        except Exception:
            detected_projects = []

    for p in detected_projects:
        name = p.get("Name") or p.get("Project")
        # ConfigFiles 可能是以逗号/换行分隔的多个文件，取第一个作为主配置
        raw_files = p.get("ConfigFiles") or p.get("ConfigPath") or ""
        files = [f.strip() for f in raw_files.replace(",", "\n").splitlines() if f.strip()]
        primary = files[0] if files else ""
        if name and primary:
            projects.append({
                "name": name,
                "path": os.path.dirname(primary),
                "config_file": primary,
                "type": "detected",
                "status": p.get("Status")
            })
            managed_files.update(files)

    # 2. 合并后的扫描路径搜索结果
    for file_path in found_files:
        if not file_path or file_path in managed_files: continue
        project_dir = os.path.dirname(file_path)
        projects.append({
            "name": os.path.basename(project_dir),
            "path": project_dir,
            "config_file": file_path,
            "type": "scanned",
            "status": "exited"
        })
        managed_files.add(file_path)

    # 3. 合并持久记忆：曾经出现过、但当前 docker compose ls 已探测不到的项目
    #    （容器被删除/更新失败后仍保留在面板中，可通过“启动/更新”一键拉起）
    listed_files = {p["config_file"] for p in projects}
    remembered = []
    for entry in remembered_entries:
        cf = (entry or {}).get("config_file")
        if not cf or cf in listed_files: continue
        remembered.append({
            "name": entry.get("name") or os.path.basename(os.path.dirname(cf)),
            "path": os.path.dirname(cf),
            "config_file": cf,
            "type": "remembered",
            "status": "exited"
        })
        listed_files.add(cf)

    if remembered:
        # "文件是否仍存在"的校验已经在第 0 步的合并脚本里做完了。
        # 如果脚本整个没跑起来（markers_seen 为空），保守地保留全部记忆条目。
        if _SCAN_SEC_FILES in markers_seen:
            alive = set(alive_files)
            remembered = [r for r in remembered if r["config_file"] in alive]

    projects.extend(remembered)

    # 4. 本地内置项目
    if service.host_config.get("type") == "local" and os.path.exists(COMPOSE_DIR):
        for d in os.listdir(COMPOSE_DIR):
            path = os.path.join(COMPOSE_DIR, d)
            cfg = os.path.join(path, "docker-compose.yml")
            if os.path.isdir(path) and cfg not in listed_files:
                projects.append({"name": d, "path": path, "config_file": cfg, "type": "internal", "status": "unknown"})

    # 5. 持久化记忆（仅内容变化时写盘，避免频繁 IO）
    new_registry = [
        {"name": p["name"], "config_file": p["config_file"]}
        for p in projects if p.get("type") != "internal" and p.get("config_file")
    ]
    old_registry = _registry_entries(config, host_id)
    key = lambda e: (e.get("name", ""), e.get("config_file", ""))
    if sorted(map(key, new_registry)) != sorted(map(key, old_registry)):
        registry_all = config.get("compose_registry", {})
        registry_all[host_id] = new_registry
        config["compose_registry"] = registry_all
        save_config(config)

    return projects

@router.get("/{host_id}/projects")
async def list_projects(host_id: str):
    # 1. 检查后端内存缓存
    if host_id in DockerService._projects_cache:
        data, ts = DockerService._projects_cache[host_id]
        if time.time() - ts < PROJECTS_CACHE_TTL:
            return data

    service = get_docker_service(host_id)

    # 在线程池中执行重型扫描任务
    projects = await asyncio.to_thread(_scan_projects, service, host_id)

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

    # 在循环外建一次 service：改前每次迭代都会调 get_docker_service()，
    # 而 DockerService 构造会做一次连接存活探测，等于每个项目多一次往返。
    service = get_docker_service(host_id)

    for p in projects:
        path = p.get("config_file") or p.get("path")
        if not path: continue
        
        # 统一处理路径：如果是目录则尝试寻找 yml
        if not path.endswith((".yml", ".yaml")):
            path = os.path.join(path, "docker-compose.yml")

        try:
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

    # 从持久记忆中剔除，避免“从视图移除”后又作为记忆项目重新出现
    registry_all = config.get("compose_registry", {})
    host_registry = registry_all.get(host_id, [])
    pruned = [e for e in host_registry if e.get("config_file") != path]
    if len(pruned) != len(host_registry):
        registry_all[host_id] = pruned
        config["compose_registry"] = registry_all
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
