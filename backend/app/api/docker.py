from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.config_manager import get_config, save_config
from app.services.docker_service import DockerService
from app.services.notification_service import NotificationService
from app.utils.logger import logger, audit_log
import uuid
import time

router = APIRouter()

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

from fastapi import APIRouter, HTTPException, Depends, Body, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from websockets.exceptions import ConnectionClosed
from typing import List, Dict, Any, Optional
import asyncio
import select

# ... (keep existing imports)

@router.websocket("/{host_id}/containers/{container_id}/exec")
async def container_exec(websocket: WebSocket, host_id: str, container_id: str, command: str = "/bin/bash"):
    await websocket.accept()
    
    try:
        service = get_docker_service(host_id)
        # 获取 Docker 交互式 Socket
        sock = service.get_container_socket(container_id, command)
        if not sock:
            await websocket.send_text("\r\n❌ 无法连接到容器终端 (可能不支持 " + command + ")\r\n")
            await websocket.close()
            return

        # 设置非阻塞模式 (兼容标准 socket 和 paramiko Channel)
        try:
            if hasattr(sock, 'setblocking'):
                sock.setblocking(False)
            elif hasattr(sock, 'settimeout'):
                sock.settimeout(0.0)
        except:
            pass

        async def socket_to_ws():
            try:
                while True:
                    await asyncio.sleep(0.02) # 稍微降低频率，防止 CPU 占用过高
                    
                    # 检查是否有数据可读
                    has_data = False
                    if hasattr(sock, 'recv_ready'): # Paramiko Channel
                        has_data = sock.recv_ready()
                    else: # Standard socket
                        r, _, _ = select.select([sock], [], [], 0.01)
                        has_data = bool(r)

                    if has_data:
                        data = sock.recv(4096)
                        if not data:
                            break
                        await websocket.send_bytes(data)
            except Exception as e:
                logger.error(f"Socket to WS error: {e}")
            finally:
                try:
                    await websocket.close()
                except:
                    pass

        read_task = asyncio.create_task(socket_to_ws())

        try:
            while True:
                # 接收前端输入
                data = await websocket.receive_text()
                # 写入 Docker Socket
                if hasattr(sock, 'sendall'):
                    sock.sendall(data.encode())
                else:
                    sock.send(data.encode())
        except (WebSocketDisconnect, ConnectionClosed):
            pass
        except Exception as e:
            logger.error(f"WS to Socket error: {e}")
        finally:
            read_task.cancel()
            try:
                sock.close()
            except:
                pass
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

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

@router.get("/{host_id}/containers")
async def list_containers(host_id: str, details: bool = True):
    service = get_docker_service(host_id)
    return await asyncio.to_thread(service.list_containers, details=details)

@router.get("/{host_id}/containers/stats")
async def get_container_stats(host_id: str):
    service = get_docker_service(host_id)
    return await asyncio.to_thread(service.get_containers_stats)

@router.get("/{host_id}/check-image-update")
async def check_single_image_update(host_id: str, image: str):
    """单镜像精准检测"""
    service = get_docker_service(host_id)
    info = await service.get_image_update_info(image)
    return {image: info}

@router.post("/{host_id}/containers/{container_id}/action")
async def container_action(host_id: str, container_id: str, action: str = Body(..., embed=True)):
    start_time = time.time()
    logger.info(f"🚀 [Docker] 收到容器操作请求: 动作={action}, 容器ID={container_id}, 主机={host_id}")
    service = get_docker_service(host_id)
    
    # 尝试获取容器名称，用于通知
    container_name = container_id
    try:
        if service.client:
            def get_name():
                return service.client.containers.get(container_id).name
            container_name = await asyncio.to_thread(get_name)
    except Exception:
        pass

    # 操作名称中文化
    action_map = {
        "start": "启动 (Start)",
        "stop": "停止 (Stop)",
        "restart": "重启 (Restart)",
        "remove": "删除 (Remove)",
        "recreate": "重构/更新 (Recreate)"
    }
    display_action = action_map.get(action, action)

    # 对于耗时操作（recreate/update），采用后台任务模式，防止前端超时
    if action in ["recreate", "update"]:
        async def run_recreate_task():
            try:
                # 记录审计日志
                audit_log(f"Docker Async Action: {action}", 0, [f"Host: {host_id}", f"Container: {container_name}"])
                
                # 执行操作
                success = await asyncio.to_thread(service.container_action, container_id, action)
                
                status_text = "成功" if success else "失败"
                logger.info(f"🏁 [Docker] 异步操作 {action} 执行完成: {status_text}")
                
                # 执行完成后的通知
                await NotificationService.emit(
                    event="docker.container_action",
                    title="Docker 容器更新结果",
                    message=f"主机: {host_id}\n容器: {container_name}\n操作: {display_action}\n结果: {status_text}"
                )
            except Exception as e:
                logger.error(f"🚨 [Docker] 异步重构任务崩溃: {e}")
                await NotificationService.emit(
                    event="docker.container_action",
                    title="Docker 容器更新异常",
                    message=f"主机: {host_id}\n容器: {container_name}\n错误: {str(e)}"
                )

        asyncio.create_task(run_recreate_task())
        return {"message": f"容器 {display_action} 任务已在后台启动，请留意系统通知", "async": True}

    # 普通操作依然同步等待
    success = await asyncio.to_thread(service.container_action, container_id, action)
    
    if not success:
        logger.error(f"❌ [Docker] 容器操作失败: {action} -> {container_id}")
        raise HTTPException(status_code=500, detail=f"Failed to perform action {action}")
    
    process_time = (time.time() - start_time) * 1000
    logger.info(f"✅ [Docker] 容器操作成功: {action} (耗时 {process_time:.1f}ms)")
    
    # 发送通知
    asyncio.create_task(NotificationService.emit(
        event="docker.container_action",
        title="Docker 容器操作提醒",
        message=f"容器: {container_name}\n操作: {display_action}\n结果: 成功"
    ))

    audit_log(f"Docker Action: {action}", process_time, [
        f"Host: {host_id}",
        f"Container: {container_id}"
    ])
    
    return {"message": f"Action {action} performed successfully"}


@router.get("/{host_id}/containers/{container_id}/logs")
async def get_container_logs(host_id: str, container_id: str, tail: int = 100):
    logger.info(f"📜 [Docker] 正在获取容器日志: {container_id} (tail={tail})")
    service = get_docker_service(host_id)
    logs = service.get_container_logs(container_id, tail)
    return {"logs": logs}

# ==================== 镜像管理 ====================

class ImagePullRequest(BaseModel):
    image: str

class ImageTagRequest(BaseModel):
    repo: str
    tag: str = "latest"

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

@router.post("/{host_id}/test")
async def test_connection(host_id: str):
    logger.info(f"🔍 [Docker] 正在测试主机连接: {host_id}")
    service = get_docker_service(host_id)
    is_ok = service.test_connection()
    if is_ok:
        logger.info(f"✨ [Docker] 主机连接测试成功: {host_id}")
    else:
        logger.error(f"💔 [Docker] 主机连接测试失败: {host_id}")
    return {"status": "ok" if is_ok else "error"}

async def run_cleanup_background(host_id: str, cmd: str, task_name: str):
    """在后台执行清理任务并发送通知"""
    logger.info(f"🧹 [Docker] 开始执行后台清理任务: {task_name} (Host: {host_id})")
    
    # 获取主机名用于通知
    config = get_config()
    hosts = config.get("docker_hosts", [])
    host_name = next((h.get("name") for h in hosts if h.get("id") == host_id), host_id)
    
    # 异步执行耗时命令
    def execute():
        service = get_docker_service(host_id)
        return service.exec_command(cmd)
    
    res = await asyncio.to_thread(execute)
    
    # 准备通知内容
    status = "成功" if res["success"] else "失败"
    message = f"主机: {host_name}\n任务: {task_name}\n状态: {status}\n\n"
    if res["stdout"]:
        message += f"输出详情:\n{res['stdout'][-500:]}" # 仅保留最后500字符
    if res["stderr"]:
        message += f"\n错误详情:\n{res['stderr']}"

    await NotificationService.emit(
        event="docker.cleanup",
        title=f"Docker {task_name}完成",
        message=message
    )
    logger.info(f"✨ [Docker] 后台清理任务完成: {task_name}")

@router.post("/{host_id}/prune-images")
async def prune_images(host_id: str, dangling: bool = Body(True, embed=True), all_unused: bool = Body(False, embed=True)):
    """清理镜像（保留接口以兼容旧版调用）"""
    # 构建命令
    cmd = "docker image prune -f"
    if all_unused:
        cmd = "docker image prune -a -f"
    elif not dangling:
        return {"message": "未选择清理选项"}
        
    asyncio.create_task(run_cleanup_background(host_id, cmd, "镜像清理"))
    return {"message": "镜像清理任务已在后台启动，完成后将通过通知告知您"}

@router.post("/{host_id}/prune-cache")
async def prune_cache(host_id: str):
    """清理构建缓存（保留接口以兼容旧版调用）"""
    asyncio.create_task(run_cleanup_background(host_id, "docker builder prune -f", "构建缓存清理"))
    return {"message": "构建缓存清理任务已在后台启动，完成后将通过通知告知您"}

@router.post("/{host_id}/prune-containers")
async def prune_containers(host_id: str):
    """清理停止的容器（保留接口以兼容旧版调用）"""
    asyncio.create_task(run_cleanup_background(host_id, "docker container prune -f", "容器清理"))
    return {"message": "容器清理任务已在后台启动，完成后将通过通知告知您"}

@router.post("/{host_id}/prune")
async def prune_all(
    host_id: str,
    images_dangling: bool = Body(False, embed=True),
    images_unused: bool = Body(False, embed=True),
    build_cache: bool = Body(False, embed=True),
    containers: bool = Body(False, embed=True),
    networks: bool = Body(False, embed=True),
):
    """
    统一清理接口：根据勾选项组合清理命令一次性执行。
    - images_dangling: 清理未标签镜像 (Dangling) -> docker image prune -f
    - images_unused:   清理所有未使用镜像 (Unused) -> docker image prune -a -f
                      （与 images_dangling 互斥，勾选此项时已包含 dangling）
    - build_cache:    清理 BuildKit/Buildx 构建缓存 -> docker builder prune -f
    - containers:     清理所有停止的容器 -> docker container prune -f
    - networks:       清理未被容器使用的网络 -> docker network prune -f
    """
    # 至少要选一项
    if not any([images_dangling, images_unused, build_cache, containers, networks]):
        return {"message": "未选择清理选项"}

    cmd_parts = []

    # 镜像清理：unused 已包含 dangling，二者只取其一
    if images_unused:
        cmd_parts.append("docker image prune -a -f")
    elif images_dangling:
        cmd_parts.append("docker image prune -f")

    if build_cache:
        cmd_parts.append("docker builder prune -f")

    if containers:
        cmd_parts.append("docker container prune -f")

    if networks:
        cmd_parts.append("docker network prune -f")

    if not cmd_parts:
        return {"message": "未选择清理选项"}

    cmd = " && ".join(cmd_parts)
    asyncio.create_task(run_cleanup_background(host_id, cmd, "资源清理"))
    return {"message": "资源清理任务已在后台启动，完成后将通过通知告知您", "command": cmd}

@router.get("/{host_id}/system-info")
async def get_system_info(host_id: str):
    """检测远程主机的 Docker 环境信息"""
    service = get_docker_service(host_id)
    
    # 检测 Docker 版本
    docker_ver = service.exec_command("docker version --format '{{.Server.Version}}' 2>/dev/null || docker -v")
    # 检测 Docker Compose 版本
    compose_ver = service.exec_command("docker compose version --short 2>/dev/null || docker-compose version --short 2>/dev/null || docker-compose -v")
    # 检测 操作系统信息
    os_info = service.exec_command("uname -snrmo")
    # 检测 Docker 服务状态
    service_status = service.exec_command("systemctl is-active docker 2>/dev/null || echo 'unknown'")

    return {
        "docker": docker_ver["stdout"].strip() if docker_ver["success"] else "未安装",
        "compose": compose_ver["stdout"].strip() if compose_ver["success"] else "未安装",
        "os": os_info["stdout"].strip() if os_info["success"] else "未知",
        "status": service_status["stdout"].strip()
    }

@router.post("/{host_id}/install-env")
async def install_docker_env(host_id: str, use_mirror: bool = Body(True, embed=True), proxy: Optional[str] = Body(None, embed=True)):
    """一键安装 Docker 和 Docker Compose"""
    service = get_docker_service(host_id)
    
    # 构造代理前缀
    proxy_prefix = f"export http_proxy={proxy} && export https_proxy={proxy} && " if proxy else ""
    
    # 使用 Docker 官方安装脚本
    mirror_cmd = " --mirror Aliyun" if use_mirror else ""
    install_cmd = f"curl -fsSL https://get.docker.com | sh -s --{mirror_cmd}"
    
    setup_cmd = (
        f"{proxy_prefix}"
        f"{install_cmd} && "
        "systemctl enable docker && systemctl start docker"
    )
    
    logger.info(f"🛠️ [Docker] 开始在主机 {host_id} 上安装环境...")
    res = service.exec_command(setup_cmd)
    
    if res["success"]:
        logger.info(f"✨ [Docker] 主机 {host_id} 环境安装完成")
    else:
        logger.error(f"❌ [Docker] 主机 {host_id} 环境安装失败: {res['stderr']}")
    
    # 发送通知
    config = get_config()
    hosts = config.get("docker_hosts", [])
    host_name = next((h.get("name") for h in hosts if h.get("id") == host_id), host_id)
    
    asyncio.create_task(NotificationService.emit(
        event="docker.host_action",
        title="Docker 环境安装结果",
        message=f"主机: {host_name}\n状态: {'成功' if res['success'] else '失败'}\n{res['stderr'] if not res['success'] else ''}"
    ))
        
    return {
        "success": res["success"],
        "stdout": res["stdout"],
        "stderr": res["stderr"]
    }

@router.post("/{host_id}/service-action")
async def docker_service_action(host_id: str, action: str = Body(..., embed=True)):
    """控制 Docker 核心服务 (start, stop, restart)"""
    service = get_docker_service(host_id)
    
    # 构造 systemctl 命令
    if action not in ["start", "stop", "restart"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    cmd = f"systemctl {action} docker"
    logger.info(f"⚙️ [Docker] 正在对主机 {host_id} 执行服务操作: {action}")
    res = service.exec_command(cmd)
    
    # 发送通知
    config = get_config()
    hosts = config.get("docker_hosts", [])
    host_name = next((h.get("name") for h in hosts if h.get("id") == host_id), host_id)
    
    asyncio.create_task(NotificationService.emit(
        event="docker.host_action",
        title="Docker 服务操作提醒",
        message=f"主机: {host_name}\n操作: {action}\n结果: {'成功' if res['success'] else '失败'}"
    ))

    return {
        "success": res["success"],
        "stdout": res["stdout"],
        "stderr": res["stderr"]
    }

import json
import os

class DaemonUpdate(BaseModel):
    config: Dict[str, Any]
    restart: bool = False

@router.get("/{host_id}/daemon-config")
async def get_daemon_config(host_id: str):
    """读取远程主机的 /etc/docker/daemon.json"""
    service = get_docker_service(host_id)
    content = service.read_file("/etc/docker/daemon.json")
    if not content:
        return {}
    try:
        return json.loads(content)
    except:
        return {"_raw": content}

@router.post("/{host_id}/daemon-config")
async def save_daemon_config(host_id: str, data: DaemonUpdate):
    """保存配置并备份"""
    service = get_docker_service(host_id)
    config = data.config
    restart = data.restart
    
    # 1. 读取旧配置用于备份
    old_content = service.read_file("/etc/docker/daemon.json")
    
    # 2. 本地备份
    if old_content:
        backup_dir = "data/backups/daemon_configs"
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        with open(f"{backup_dir}/{host_id}_{timestamp}.json", "w") as f:
            f.write(old_content)
            
        # 3. 远程备份 (daemon.json.bak)
        service.exec_command("cp /etc/docker/daemon.json /etc/docker/daemon.json.bak")

    # 4. 写入新配置
    new_content = json.dumps(config, indent=4)
    if not service.write_file("/etc/docker/daemon.json", new_content):
        raise HTTPException(status_code=500, detail="写入文件失败，请检查 SSH 账户是否有 root 权限")

    # 5. 重启 Docker (如果勾选)
    restart_res = None
    if restart:
        restart_res = service.exec_command("systemctl daemon-reload && systemctl restart docker")

    return {
        "message": "配置已保存并备份", 
        "restart_result": restart_res
    }

@router.get("/{host_id}/daemon-config/raw")
async def get_daemon_config_raw(host_id: str):
    """获取原始 daemon.json 文本"""
    service = get_docker_service(host_id)
    content = service.read_file("/etc/docker/daemon.json")
    return {"content": content or "{}"}

@router.post("/{host_id}/daemon-config/raw")
async def save_daemon_config_raw(host_id: str, data: Dict[str, Any] = Body(...)):
    """保存原始 daemon.json 文本"""
    host_id = host_id
    content = data.get("content")
    restart = data.get("restart", False)
    
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
        
    # 校验 JSON 格式
    try:
        json_obj = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON 格式错误: {str(e)}")
        
    # 重用之前的保存逻辑 (会自动备份)
    return await save_daemon_config(host_id, DaemonUpdate(config=json_obj, restart=restart))

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

class DockerAutoUpdateSettings(BaseModel):
    enabled: bool
    type: str # 'cron' or 'interval'
    value: str

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