"""容器相关接口：终端 WebSocket、列表、统计、操作、日志。"""
import asyncio
import select
import time

from fastapi import APIRouter, Body, HTTPException, WebSocket, WebSocketDisconnect
from app.services.docker_service import DockerService
from app.services.notification_service import NotificationService
from app.utils.logger import logger, audit_log

from .common import get_docker_service

router = APIRouter()

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
        except Exception:
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
                except Exception:
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
            except Exception:
                pass
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass



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

    # 对于耗时操作（recreate/update），采用后台任务模式，防止前端超时；
    # 同时注册可轮询/可取消的任务，支持进度展示与二次点击防重。
    if action in ["recreate", "update"]:
        existing_task_id = DockerService.get_active_update_task_id(host_id, container_id)
        if existing_task_id:
            return {
                "already_running": True,
                "task_id": existing_task_id,
                "message": "该容器已有更新任务正在进行，请勿重复操作",
                "async": True,
            }

        task_id = DockerService.register_update_task(host_id, container_id, container_name, "")
        if not task_id:
            # 极端并发下 register 自身也会防重，此时取回已存在任务
            existing_task_id = DockerService.get_active_update_task_id(host_id, container_id)
            if existing_task_id:
                return {
                    "already_running": True,
                    "task_id": existing_task_id,
                    "message": "该容器已有更新任务正在进行，请勿重复操作",
                    "async": True,
                }
            raise HTTPException(status_code=500, detail="无法创建更新任务")

        cancel_event = DockerService._get_update_task_raw(task_id)["cancel_event"]

        async def run_recreate_task():
            try:
                # 记录审计日志
                audit_log(f"Docker Async Action: {action}", 0, [f"Host: {host_id}", f"Container: {container_name}"])
                
                # 执行操作（流式进度写入任务表）
                await asyncio.to_thread(service.run_container_update, task_id, container_id, cancel_event)
                
                task = DockerService.get_update_task(task_id) or {}
                status = task.get("status")
                status_text = {
                    "success": "成功",
                    "failed": "失败",
                    "cancelled": "已终止",
                }.get(status, status or "完成")
                logger.info(f"🏁 [Docker] 异步操作 {action} 执行完成: {status_text}")
                
                # 执行完成后的通知
                await NotificationService.emit(
                    event="docker.container_action",
                    title="Docker 容器更新结果",
                    message=(
                        f"主机: {host_id}\n容器: {container_name}\n"
                        f"操作: {display_action}\n结果: {status_text}"
                        + (f"\n错误: {task.get('error')}" if task.get("error") else "")
                    )
                )
            except Exception as e:
                logger.error(f"🚨 [Docker] 异步重构任务崩溃: {e}")
                await NotificationService.emit(
                    event="docker.container_action",
                    title="Docker 容器更新异常",
                    message=f"主机: {host_id}\n容器: {container_name}\n错误: {str(e)}"
                )

        asyncio.create_task(run_recreate_task())
        return {
            "message": f"容器 {display_action} 任务已启动，可在容器卡片查看进度",
            "async": True,
            "task_id": task_id,
        }

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


@router.get("/{host_id}/containers/{container_id}/update/{task_id}")
async def get_container_update_progress(host_id: str, container_id: str, task_id: str):
    """轮询容器更新任务进度（只读内存，不产生 SSH 往返）。"""
    task = DockerService.get_update_task(task_id)
    if not task or task.get("host_id") != host_id or task.get("container_id") != container_id:
        raise HTTPException(status_code=404, detail="更新任务不存在")
    return task


@router.post("/{host_id}/containers/{container_id}/update/{task_id}/cancel")
async def cancel_container_update(host_id: str, container_id: str, task_id: str):
    """请求终止容器更新任务（在安全点停止，拉取阶段可即时中止）。"""
    task = DockerService.get_update_task(task_id)
    if not task or task.get("host_id") != host_id or task.get("container_id") != container_id:
        raise HTTPException(status_code=404, detail="更新任务不存在")
    if task.get("done"):
        return {"message": "任务已结束", "cancelled": False}
    cancelled = DockerService.request_cancel_update(task_id)
    return {
        "message": "已请求终止，将在安全点停止（拉取阶段可即时中止；重建阶段会安全收尾）" if cancelled else "任务已结束",
        "cancelled": cancelled,
    }


@router.get("/{host_id}/containers/{container_id}/logs")
async def get_container_logs(host_id: str, container_id: str, tail: int = 100):
    logger.info(f"📜 [Docker] 正在获取容器日志: {container_id} (tail={tail})")
    start_time = time.time()
    service = get_docker_service(host_id)
    logs = service.get_container_logs(container_id, tail)
    log_lines = len(logs.splitlines()) if isinstance(logs, str) else (len(logs) if logs else 0)
    logger.info(f"✅ [Docker] 容器日志获取完成 (耗时 {time.time() - start_time:.2f}s, 行数: {log_lines})")
    return {"logs": logs}

