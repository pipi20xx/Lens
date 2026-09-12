"""维护接口：连接测试、资源清理、环境安装、服务控制、daemon.json 管理。"""
import json
import os
import time
import asyncio

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body

from app.core.config_manager import get_config
from app.services.notification_service import NotificationService
from app.utils.logger import logger

from .common import get_docker_service, DaemonUpdate

router = APIRouter()

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
    start_time = time.time()
    res = service.exec_command(cmd)

    if res["success"]:
        logger.info(f"✅ [Docker] 服务操作成功: {action} (耗时 {time.time() - start_time:.2f}s, Host: {host_id})")
    else:
        logger.error(f"❌ [Docker] 服务操作失败: {action} (Host: {host_id}): {res['stderr']}")

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



@router.get("/{host_id}/daemon-config")
async def get_daemon_config(host_id: str):
    """读取远程主机的 /etc/docker/daemon.json"""
    service = get_docker_service(host_id)
    content = service.read_file("/etc/docker/daemon.json")
    if not content:
        return {}
    try:
        return json.loads(content)
    except Exception:
        return {"_raw": content}

@router.post("/{host_id}/daemon-config")
async def save_daemon_config(host_id: str, data: DaemonUpdate):
    """保存配置并备份"""
    service = get_docker_service(host_id)
    config = data.config
    restart = data.restart
    start_time = time.time()

    logger.info(f"🚀 [Docker] 保存 daemon.json 配置 (Host: {host_id}, 重启: {restart})")

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

    logger.info(f"✅ [Docker] daemon.json 配置保存完成 (耗时 {time.time() - start_time:.2f}s, Host: {host_id}, 已重启: {bool(restart)})")
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

