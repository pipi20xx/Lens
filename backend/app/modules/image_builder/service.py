import os
import re
import uuid
import asyncio
import subprocess
import hashlib
import tempfile
import docker
import paramiko
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlparse, urlunparse

from . import models, schemas
from app.utils.logger import logger
from app.core.config_manager import get_config, save_config
from app.services.docker_service import DockerService

BUILD_LOG_DIR = Path("/app/data/logs/builds")
BUILD_LOG_DIR.mkdir(parents=True, exist_ok=True)

TASK_LOG_SENTINEL = "--- TASK_COMPLETED ---"

class ImageBuilderService:
    # --- Project CRUD (JSON) ---
    @staticmethod
    async def get_projects(db: Any = None) -> List[Dict[str, Any]]:
        config = get_config()
        return config.get("build_projects", [])

    @staticmethod
    async def create_project(db: Any, project: schemas.ProjectCreate) -> Dict[str, Any]:
        config = get_config()
        projects = config.get("build_projects", [])
        new_project = project.dict()
        new_project["id"] = str(uuid.uuid4())
        projects.append(new_project)
        config["build_projects"] = projects
        save_config(config)
        return new_project

    @staticmethod
    async def get_project(db: Any, project_id: str) -> Optional[Dict[str, Any]]:
        config = get_config()
        projects = config.get("build_projects", [])
        return next((p for p in projects if p["id"] == project_id), None)

    @staticmethod
    async def update_project(db: Any, project_id: str, project_in: schemas.ProjectUpdate) -> Optional[Dict[str, Any]]:
        config = get_config()
        projects = config.get("build_projects", [])
        for i, p in enumerate(projects):
            if p["id"] == project_id:
                update_data = project_in.dict(exclude_unset=True)
                projects[i].update(update_data)
                config["build_projects"] = projects
                save_config(config)
                return projects[i]
        return None

    @staticmethod
    async def delete_project(db: Any, project_id: str) -> bool:
        config = get_config()
        projects = config.get("build_projects", [])
        new_projects = [p for p in projects if p["id"] != project_id]
        if len(new_projects) == len(projects): return False
        config["build_projects"] = new_projects
        save_config(config)
        return True

    # --- Registry CRUD (JSON) ---
    @staticmethod
    async def get_registries(db: Any = None) -> List[Dict[str, Any]]:
        config = get_config()
        return config.get("build_registries", [])

    @staticmethod
    async def create_registry(db: Any, registry: schemas.RegistryCreate) -> Dict[str, Any]:
        config = get_config()
        registries = config.get("build_registries", [])
        new_reg = registry.dict()
        new_reg["id"] = str(uuid.uuid4())
        registries.append(new_reg)
        config["build_registries"] = registries
        save_config(config)
        return new_reg

    @staticmethod
    async def get_registry(db: Any, registry_id: str) -> Optional[Dict[str, Any]]:
        config = get_config()
        registries = config.get("build_registries", [])
        return next((r for r in registries if r["id"] == registry_id), None)

    @staticmethod
    async def update_registry(db: Any, registry_id: str, registry_in: schemas.RegistryUpdate) -> Optional[Dict[str, Any]]:
        config = get_config()
        registries = config.get("build_registries", [])
        for i, r in enumerate(registries):
            if r["id"] == registry_id:
                update_data = registry_in.dict(exclude_unset=True)
                registries[i].update(update_data)
                config["build_registries"] = registries
                save_config(config)
                return registries[i]
        return None

    @staticmethod
    async def delete_registry(db: Any, registry_id: str) -> bool:
        config = get_config()
        registries = config.get("build_registries", [])
        new_regs = [r for r in registries if r["id"] != registry_id]
        if len(new_regs) == len(registries): return False
        config["build_registries"] = new_regs
        save_config(config)
        return True

    @staticmethod
    async def test_registry(db: Any, registry_id: str):
        registry = await ImageBuilderService.get_registry(None, registry_id)
        if not registry: return {"success": False, "message": "仓库配置不存在"}
        
        credential = None
        if registry.get("credential_id"):
            credential = await ImageBuilderService.get_credential(None, registry["credential_id"])
        
        raw_url = registry["url"].replace("https://", "").replace("http://", "")
        protocol = "https" if registry.get("is_https", True) else "http"
        api_url = f"{protocol}://{raw_url.rstrip('/')}/v2/"

        try:
            requests.get(api_url, timeout=5, verify=False)
        except Exception:
            if registry.get("is_https", True):
                try:
                    http_test_url = f"http://{raw_url.rstrip('/')}/v2/"
                    h_resp = requests.get(http_test_url, timeout=3)
                    if h_resp.status_code in [200, 401]:
                        return {"success": False, "message": f"❌ 协议不匹配: 该仓库似乎只支持 HTTP，请切换设置"}
                except: pass
            return {"success": False, "message": f"连接失败: 无法通过 {protocol.upper()} 访问该地址"}

        if credential:
            config = get_config()
            hosts = config.get("docker_hosts", [])
            host_config = hosts[0] if hosts else {"type": "local", "name": "Local Host"}
            service = DockerService(host_config)
            login_cmd = f"echo \"{credential['encrypted_password']}\" | docker login -u \"{credential['username']}\" --password-stdin {raw_url}"
            res = service.exec_command(login_cmd, log_error=False)
            if res["success"]: return {"success": True, "message": f"✅ 登录成功: 协议和凭据均已验证"}
            else: return {"success": False, "message": f"鉴权失败: {(res['stderr'] or res['stdout'])[:200]}"}
        else:
            return {"success": True, "message": f"✅ 连接成功 ({protocol.upper()}): 该地址有效"}

    # --- Credential CRUD (JSON) ---
    @staticmethod
    async def get_credentials(db: Any = None) -> List[Dict[str, Any]]:
        config = get_config()
        return config.get("build_credentials", [])

    @staticmethod
    async def create_credential(db: Any, cred: schemas.CredentialCreate) -> Dict[str, Any]:
        config = get_config()
        creds = config.get("build_credentials", [])
        new_cred = {
            "id": str(uuid.uuid4()), "name": cred.name, "username": cred.username, 
            "encrypted_password": cred.password
        }
        creds.append(new_cred)
        config["build_credentials"] = creds
        save_config(config)
        return new_cred

    @staticmethod
    async def get_credential(db: Any, cred_id: str) -> Optional[Dict[str, Any]]:
        config = get_config()
        creds = config.get("build_credentials", [])
        return next((c for c in creds if c["id"] == cred_id), None)

    @staticmethod
    async def update_credential(db: Any, cred_id: str, cred_in: schemas.CredentialUpdate) -> Optional[Dict[str, Any]]:
        config = get_config()
        creds = config.get("build_credentials", [])
        for i, c in enumerate(creds):
            if c["id"] == cred_id:
                update_data = cred_in.dict(exclude_unset=True)
                if 'password' in update_data:
                    if update_data['password']: creds[i]['encrypted_password'] = update_data['password']
                    del update_data['password']
                creds[i].update(update_data)
                config["build_credentials"] = creds
                save_config(config)
                return creds[i]
        return None

    @staticmethod
    async def delete_credential(db: Any, cred_id: str) -> bool:
        config = get_config()
        creds = config.get("build_credentials", [])
        new_creds = [c for c in creds if c["id"] != cred_id]
        if len(new_creds) == len(creds): return False
        config["build_credentials"] = new_creds
        save_config(config)
        return True

    # --- Proxy CRUD (JSON) ---
    @staticmethod
    async def get_proxies(db: Any = None) -> List[Dict[str, Any]]:
        config = get_config()
        return config.get("build_proxies", [])

    @staticmethod
    async def create_proxy(db: Any, proxy: schemas.ProxyCreate) -> Dict[str, Any]:
        config = get_config()
        proxies = config.get("build_proxies", [])
        new_proxy = proxy.dict()
        new_proxy["id"] = str(uuid.uuid4())
        proxies.append(new_proxy)
        config["build_proxies"] = proxies
        save_config(config)
        return new_proxy

    @staticmethod
    async def get_proxy(db: Any, proxy_id: str) -> Optional[Dict[str, Any]]:
        config = get_config()
        proxies = config.get("build_proxies", [])
        return next((p for p in proxies if p["id"] == proxy_id), None)

    @staticmethod
    async def update_proxy(db: Any, proxy_id: str, proxy_in: schemas.ProxyUpdate) -> Optional[Dict[str, Any]]:
        config = get_config()
        proxies = config.get("build_proxies", [])
        for i, p in enumerate(proxies):
            if p["id"] == proxy_id:
                update_data = proxy_in.dict(exclude_unset=True)
                proxies[i].update(update_data)
                config["build_proxies"] = proxies
                save_config(config)
                return proxies[i]
        return None

    @staticmethod
    async def delete_proxy(db: Any, proxy_id: str) -> bool:
        config = get_config()
        proxies = config.get("build_proxies", [])
        new_proxies = [p for p in proxies if p["id"] != proxy_id]
        if len(new_proxies) == len(proxies): return False
        config["build_proxies"] = new_proxies
        save_config(config)
        return True

    # --- System Info ---
    @staticmethod
    async def get_system_info(host_id: str):
        config = get_config()
        hosts = config.get("docker_hosts", [])
        host_config = next((h for h in hosts if h.get("id") == host_id), None)
        if not host_config: return {"error": "Host not found"}
        service = DockerService(host_config)
        info = {"docker_version": "Unknown", "buildx_version": "Not Found", "builders": [], "platforms": []}
        try:
            res = service.exec_command("docker version --format '{{.Server.Version}}'")
            if res["success"]: info["docker_version"] = res["stdout"].strip()
            res = service.exec_command("docker buildx version")
            if res["success"]: info["buildx_version"] = res["stdout"].strip()
            res = service.exec_command("docker buildx inspect")
            if res["success"] and res["stdout"]:
                match = re.search(r"Platforms:\s*(.+)", res["stdout"])
                if match:
                    plat_str = match.group(1).strip()
                    info["platforms"] = sorted(list(set(p.strip() for p in plat_str.split(",") if p.strip())))
            res = service.exec_command("docker buildx ls")
            if res["success"]: info["builders"] = res["stdout"].splitlines()
        except Exception as e: logger.error(f"Error getting remote system info: {e}")
        return info

    @staticmethod
    async def setup_buildx_env(host_id: str, proxy_id: Optional[str] = None):
        """一键初始化构建环境：安装 QEMU, 配置 Buildx 等 (异步后台任务)"""
        config = get_config()
        hosts = config.get("docker_hosts", [])
        host_config = next((h for h in hosts if h.get("id") == host_id), None)
        if not host_config: 
            return {"success": False, "message": "Host not found"}

        # 定义后台执行任务
        async def background_setup():
            from app.services.notification_service import NotificationService
            service = DockerService(host_config)
            host_name = host_config.get('name', host_id)
            
            async def notify(msg: str):
                logger.info(f"🛠️ [环境初始化] {msg} (主机: {host_name})")
                await NotificationService.emit(
                    event="image_builder.setup_progress",
                    title="环境初始化进度",
                    message=f"主机: {host_name}\n进度: {msg}"
                )

            try:
                proxy_env = ""
                if proxy_id:
                    proxy = await ImageBuilderService.get_proxy(None, proxy_id)
                    if proxy:
                        url = proxy["url"]
                        if proxy.get("username") and proxy.get("password"):
                            parsed = urlparse(url)
                            netloc = f"{proxy['username']}:{proxy['password']}@{parsed.netloc}"
                            url = urlunparse(parsed._replace(netloc=netloc))
                        proxy_env = f"--driver-opt env.http_proxy={url} --driver-opt env.https_proxy={url} --driver-opt env.no_proxy=localhost,127.0.0.1"
                        await notify(f"已绑定构建代理: {proxy['url']}")

                # 1. 安装 QEMU (耗时较长，多架构支持)
                await notify("正在安装 QEMU 多架构仿真支持 (耗时较长)...")
                await asyncio.to_thread(service.exec_command, "docker run --privileged --rm tonistiigi/binfmt --install all")

                # 2. 清理旧构建器
                await notify("正在清理旧构建器 (lens-builder)...")
                await asyncio.to_thread(service.exec_command, "docker buildx rm lens-builder", log_error=False)

                # 3. 创建新构建器 (并配置代理)
                await notify("正在创建并配置专用构建器 (lens-builder)...")
                create_cmd = f"docker buildx create --name lens-builder --driver docker-container --driver-opt network=host {proxy_env} --use"
                res = await asyncio.to_thread(service.exec_command, create_cmd)
                
                # 4. 预热/引导
                await notify("正在执行构建器预引导 (Bootstrap)...")
                await asyncio.to_thread(service.exec_command, "docker buildx inspect --bootstrap")

                await notify("✨ 环境初始化任务已成功完成！")
                
            except Exception as e:
                logger.error(f"🚨 [环境初始化] 失败: {e}")
                await NotificationService.emit(
                    event="image_builder.setup_progress",
                    title="环境初始化失败",
                    message=f"主机: {host_name}\n原因: {str(e)}"
                )

        # 启动后台任务
        asyncio.create_task(background_setup())
        
        return {
            "success": True, 
            "message": "初始化任务已在后台启动，请关注系统通知进度",
            "async": True
        }

    # --- Task Logic (DB) ---
    @staticmethod
    async def get_task_logs(db: AsyncSession, project_id: str) -> List[models.BuildTaskLog]:
        result = await db.execute(select(models.BuildTaskLog).where(models.BuildTaskLog.project_id == project_id).order_by(models.BuildTaskLog.created_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def create_task_log(db: AsyncSession, project_id: str, tag: str, image_name: str = None, platforms: str = None, host_name: str = None) -> str:
        task_id = str(uuid.uuid4())
        db_task = models.BuildTaskLog(
            id=task_id, project_id=project_id, tag=tag,
            image_name=image_name, platforms=platforms, host_name=host_name
        )
        db.add(db_task)
        await db.commit()
        return task_id

    @staticmethod
    async def update_task_status(db: AsyncSession, task_id: str, status: str):
        await db.execute(update(models.BuildTaskLog).where(models.BuildTaskLog.id == task_id).values(
            status=status, completed_at=func.now()
        ))
        await db.commit()

    @staticmethod
    async def delete_task_log(db: AsyncSession, task_id: str):
        await db.execute(delete(models.BuildTaskLog).where(models.BuildTaskLog.id == task_id))
        await db.commit()
        log_path = BUILD_LOG_DIR / f"{task_id}.log"
        if log_path.exists():
            try: os.remove(log_path)
            except: pass
        return True

    @staticmethod
    async def delete_all_task_logs(db: AsyncSession):
        # 1. 删除所有数据库记录
        await db.execute(delete(models.BuildTaskLog))
        await db.commit()
        
        # 2. 清理所有物理日志文件
        import glob
        for log_file in glob.glob(str(BUILD_LOG_DIR / "*.log")):
            try: os.remove(log_file)
            except: pass
        return True

    @staticmethod
    def run_docker_task_sync(task_id: str, project_dict: dict, tag_input: str, cred_dict: Optional[dict], proxy_dict: Optional[dict], host_config: dict):
        log_file_path = BUILD_LOG_DIR / f"{task_id}.log"
        def log_to_file(message: str):
            with open(log_file_path, "a", encoding="utf-8") as f: f.write(message.strip() + "\n")
        service = DockerService(host_config)
        tags = [t.strip() for t in re.split(r'[,，|]', tag_input) if t.strip()]
        if not tags: tags = ["latest"]
        p = project_dict
        platforms = [plat.strip() for plat in p.get('platforms', 'linux/amd64').split(',') if plat.strip()]
        final_status = "FAILED"
        temp_builder_name = ""
        temp_config_path = f"/tmp/lens-buildkit-{task_id[:8]}.toml"
        try:
            log_to_file(f"✅ 远程构建任务已启动... (主机: {host_config.get('name')})")
            log_to_file(f"\n--- 正在准备构建环境 ---")
            reg_url = p.get('registry_url', 'docker.io')
            if "://" in reg_url: reg_host = urlparse(reg_url).netloc
            else:
                reg_host = urlparse(f"https://{reg_url}").netloc
                if not reg_host: reg_host = reg_url.split('/')[0]
            is_https = p.get('is_https', True)
            builder_to_use = "default"
            if not is_https:
                log_to_file(f"--- 🛠️ 构建模式: 检测到 HTTP 仓库，正在配置 BuildKit 信任列表: {reg_host} ---")
                config_content = f'[registry.\"{reg_host}\"]\n  http = true\n  insecure = true\n'
                if service.write_file(temp_config_path, config_content):
                    temp_builder_name = f"lens-task-{task_id[:8]}"
                    create_cmd = f"docker buildx create --name {temp_builder_name} --driver docker-container --driver-opt network=host --config {temp_config_path}"
                    res = service.exec_command(create_cmd)
                    if res["success"]:
                        builder_to_use = temp_builder_name
                        log_to_file(f"--- 🚀 模式应用: HTTP 专用构建器 ({builder_to_use}, Driver: docker-container) ---")
                    else: log_to_file(f"⚠️ 模式应用失败: 无法创建专用构建器，将尝试回退至默认模式: {res['stderr']}")
            else:
                check_builder = service.exec_command("docker buildx inspect lens-builder", log_error=False)
                if check_builder["success"]:
                    builder_to_use = "lens-builder"
                    log_to_file(f"--- 🚀 构建模式: 专用容器构建 (Builder: lens-builder, Driver: docker-container) ---")
                else: log_to_file(f"--- 💻 构建模式: 宿主机原生构建 (Builder: default, Driver: docker) ---")
            if cred_dict:
                log_to_file(f"--- 正在远程登录仓库: {reg_url} ---")
                login_cmd = f"echo \"{cred_dict['encrypted_password']}\" | docker login -u \"{cred_dict['username']}\" --password-stdin {reg_url}"
                res = service.exec_command(login_cmd)
                if not res["success"]:
                    error_msg = f"❌ 登录失败: {res['stderr']}"
                    log_to_file(error_msg)
                    raise Exception(f"Docker 登录失败，无法继续推送。请检查凭据或网络连接。\n详情: {res['stderr']}")
                else:
                    log_to_file("--- 登录成功 ---")
            build_args = []
            if proxy_dict:
                url = proxy_dict['url']
                if proxy_dict.get('username') and proxy_dict.get('password'):
                    parsed = urlparse(url)
                    netloc = f"{proxy_dict['username']}:{proxy_dict['password']}@{parsed.netloc}"
                    url = urlunparse(parsed._replace(netloc=netloc))
                log_to_file(f"--- 🚀 注入构建代理: {proxy_dict['url']} ---")
                for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']: build_args.append(f"--build-arg {key}={url}")
            if reg_host in ["docker.io", "index.docker.io", "registry-1.docker.io", ""]:
                repo_base = p['repo_image_name']
                log_to_file(f"--- 目标仓库判定为: Docker Hub ---")
            else:
                repo_base = f"{reg_host}/{p['repo_image_name']}".replace("//", "/")
                log_to_file(f"--- 目标仓库判定为私有仓库: {reg_host} ---")
            tag_args = " ".join([f"-t {repo_base}:{t}" for t in tags])
            cache_args = []
            if not p.get('no_cache'):
                primary_tag = tags[0]
                cache_args.append(f"--cache-from=type=registry,ref={repo_base}:{primary_tag}")
                cache_args.append("--cache-to=type=inline")
                log_to_file(f"--- ♻️ 缓存策略: 尝试复用远程缓存 (初次构建报错 NotFound 属正常现象) ---")
            else:
                cache_args.append("--no-cache")
                log_to_file("--- ⚡ 缓存策略: 强制无缓存构建 ---")
            log_to_file(f"--- 开始远程构建与推送 (平台: {','.join(platforms)}, Tags: {' / '.join(tags)}) ---")
            build_cmd = f"docker buildx build --builder {builder_to_use} --platform {','.join(platforms)} -f {p['dockerfile_path']} {tag_args} {' '.join(build_args)} {' '.join(cache_args)} --push ."
            log_to_file(f"执行命令: {build_cmd}")
            if host_config.get("type") == "ssh":
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(host_config['ssh_host'], port=host_config.get('ssh_port', 22), username=host_config.get('ssh_user'), password=host_config.get('ssh_pass'))
                stdin, stdout, stderr = ssh.exec_command(f"cd {p['build_context']} && {build_cmd}")
                while not stdout.channel.exit_status_ready():
                    if stdout.channel.recv_ready(): log_to_file(stdout.channel.recv(1024).decode('utf-8', 'ignore'))
                    if stderr.channel.recv_stderr_ready(): log_to_file(stderr.channel.recv_stderr(1024).decode('utf-8', 'ignore'))
                    import time
                    time.sleep(0.1)
                while stdout.channel.recv_ready(): log_to_file(stdout.channel.recv(1024).decode('utf-8', 'ignore'))
                while stderr.channel.recv_stderr_ready(): log_to_file(stderr.channel.recv_stderr(1024).decode('utf-8', 'ignore'))
                exit_status = stdout.channel.recv_exit_status()
                log_to_file(f"--- 进程退出，退出码: {exit_status} ---")
                if exit_status == 0: final_status = "SUCCESS"
                ssh.close()
            else:
                res = service.exec_command(build_cmd, cwd=p['build_context'])
                log_to_file(res["stdout"] + res["stderr"])
                log_to_file(f"--- 本地进程执行完毕，结果: {'成功' if res['success'] else '失败'} ---")
                if res["success"]: final_status = "SUCCESS"
        except Exception as e: 
            log_to_file(f"\n--- ❌ 发生严重错误 ---\n{e}")
        finally:
            if temp_builder_name:
                log_to_file(f"--- 🧹 正在清理临时构建环境: {temp_builder_name} ---")
                service.exec_command(f"docker buildx rm {temp_builder_name}", log_error=False)
            if os.path.exists(temp_config_path):
                try: os.remove(temp_config_path)
                except: pass
            service.exec_command(f"rm -f {temp_config_path}", log_error=False)
            log_to_file(TASK_LOG_SENTINEL)
            
            try:
                from app.services.notification_service import NotificationService
                status_text = "成功" if final_status == "SUCCESS" else "失败"
                summary = f"镜像构建{status_text}: {p['name']} ({repo_base}:{tags[0]})"
                logger.info(f"🚀 [镜像构建] {summary} | 主机: {host_config.get('name')}")
                asyncio.run(NotificationService.emit(event="image_builder.task_completed", title="Lens 镜像构建任务报告", message=(f"项目名称: {p['name']}\n目标镜像: {repo_base}\n标签版本: {', '.join(tags)}\n构建主机: {host_config.get('name')}\n最终状态: {status_text}\n结束时间: {datetime.now().strftime('%H:%M:%S')}")))
            except Exception: pass
        return final_status

    @staticmethod
    async def start_build_task(db: AsyncSession, project_id: str, tag: str):
        project = await ImageBuilderService.get_project(None, project_id)
        if not project: return
        config = get_config()
        hosts = config.get("docker_hosts", [])
        host_config = next((h for h in hosts if h.get("id") == project.get("host_id")), None)
        if not host_config: host_config = {"type": "local", "name": "Local Host"}
        registry = await ImageBuilderService.get_registry(None, project.get("registry_id")) if project.get("registry_id") else None
        credential = await ImageBuilderService.get_credential(None, registry.get("credential_id")) if registry and registry.get("credential_id") else None
        proxy = await ImageBuilderService.get_proxy(None, project.get("proxy_id")) if project.get("proxy_id") else None
        # 计算完整镜像地址（与 run_docker_task_sync 中的逻辑保持一致）
        reg_url = registry["url"] if registry else "docker.io"
        if "://" in reg_url:
            reg_host = urlparse(reg_url).netloc
        else:
            reg_host = urlparse(f"https://{reg_url}").netloc
            if not reg_host:
                reg_host = reg_url.split('/')[0]
        if reg_host in ["docker.io", "index.docker.io", "registry-1.docker.io", ""]:
            repo_base = project["repo_image_name"]
        else:
            repo_base = f"{reg_host}/{project['repo_image_name']}".replace("//", "/")
        # 支持多 Tag：取第一个作为展示用完整镜像地址
        first_tag = [t.strip() for t in re.split(r'[,，|]', tag) if t.strip()]
        display_tag = first_tag[0] if first_tag else tag
        full_image_name = f"{repo_base}:{display_tag}"
        platforms_str = project.get("platforms", "linux/amd64")
        host_name = host_config.get("name", "Local Host")

        task_id = await ImageBuilderService.create_task_log(
            db, project_id, tag, image_name=full_image_name, platforms=platforms_str, host_name=host_name
        )
        project_dict = {
            "name": project["name"], "build_context": project["build_context"], "dockerfile_path": project["dockerfile_path"],
            "local_image_name": project["local_image_name"], "repo_image_name": project["repo_image_name"],
            "no_cache": project.get("no_cache", False), "auto_cleanup": project.get("auto_cleanup", True),
            "platforms": project.get("platforms", "linux/amd64"), "registry_url": registry["url"] if registry else "docker.io",
            "is_https": registry.get("is_https", True) if registry else True
        }
        cred_dict = {"username": credential["username"], "encrypted_password": credential["encrypted_password"], "registry_url": registry["url"]} if credential else None
        proxy_dict = {"url": proxy["url"], "username": proxy.get("username"), "password": proxy.get("password")} if proxy else None
        def task_wrapper():
            from app.db.session import AsyncSessionLocal
            import asyncio
            status = ImageBuilderService.run_docker_task_sync(task_id, project_dict, tag, cred_dict, proxy_dict, host_config)
            async def update_db():
                async with AsyncSessionLocal() as new_db: await ImageBuilderService.update_task_status(new_db, task_id, status)
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(update_db())
            except: pass
        asyncio.create_task(asyncio.to_thread(task_wrapper))
        return task_id