import warnings
# 提前抑制 cryptography 库关于 TripleDES 的弃用警告 (Paramiko 依赖引起)
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
except ImportError:
    pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import router as api_router
from app.api.system import CURRENT_VERSION
from app.utils.logger import logger, audit_log
from sqlalchemy import select
from app.db.session import engine, Base, get_db
from app.models import * 
from app.models.user import User
from app.utils.auth import get_password_hash
from app.utils.audit import add_audit_log, mask_sensitive_data
from app.services.config_service import ConfigService
import asyncio
import os
import time
import json

# 确保数据目录存在
os.makedirs("/app/data/nav_icons", exist_ok=True)
os.makedirs("/app/data/logs/audit", exist_ok=True)

app = FastAPI(
    title="Lens API",
    version=CURRENT_VERSION.lstrip('v'),
    docs_url=None,
    redoc_url=None,
)
# 全局审计与性能监控中间件
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    
    # --- 1. 核心安全拦截逻辑 ---
    # 只保留必须公开的接口：登录、图片代理、API 文档、Webhook 接收端点
    public_paths = ["/api/auth/login", "/api/playback-report/image-proxy", "/api/system/docs", "/api/system/openapi.json"]
    is_api = path.startswith("/api")
    # 使用精确匹配，避免子路径绕过；Webhook 接收端点支持路径后缀，使用前缀匹配
    is_public = path in public_paths or path == "/" or path.startswith("/api/webhook/receive")
    
    if is_api and not is_public:
        # 动态导入以避免循环依赖
        from app.utils.auth import decode_access_token
        
        api_auth_enabled_val = await ConfigService.get("auth_enabled", True)
        api_auth_enabled = api_auth_enabled_val is True or str(api_auth_enabled_val).lower() == "true"
        
        if api_auth_enabled:
            auth_header = request.headers.get("Authorization")
            token = auth_header.replace("Bearer ", "") if auth_header and auth_header.startswith("Bearer ") else None
            
            valid = False
            if token:
                # 检查静态 Token
                static_token = await ConfigService.get("api_token")
                if static_token and token == static_token:
                    valid = True
                else:
                    # 检查 JWT Token
                    from app.utils.auth import decode_access_token
                    from app.db.session import AsyncSessionLocal
                    from sqlalchemy import select
                    from app.models.user import User
                    
                    payload = decode_access_token(token)
                    if payload and payload.get("type") != "2fa_pending":
                        # 必须有 session_id 和密码指纹
                        session_id = payload.get("sid")
                        token_ps = payload.get("ps")
                        
                        if not session_id or not token_ps:
                            valid = False
                        else:
                            # 验证会话是否存在且活跃
                            from app.services.session_service import get_session_by_id
                            from app.utils.time import get_local_time
                            async with AsyncSessionLocal() as db:
                                session = await get_session_by_id(db, session_id)
                                if not session:
                                    valid = False
                                else:
                                    # 检查会话是否已过期
                                    now = get_local_time()
                                    if now.tzinfo is not None:
                                        now = now.replace(tzinfo=None)
                                    
                                    if session.expires_at < now:
                                        valid = False
                                    else:
                                        # 验证密码指纹
                                        result = await db.execute(select(User).where(User.id == session.user_id))
                                        user = result.scalars().first()
                                        if not user:
                                            valid = False
                                        else:
                                            current_ps = user.hashed_password[:16]
                                            if token_ps != current_ps:
                                                valid = False
                                            else:
                                                # 更新会话最后活动时间
                                                from app.services.session_service import update_session_activity
                                                await update_session_activity(db, session_id)
                                                valid = True
            
            if not valid:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=401, content={"detail": "API Authentication Required"})

    # --- 2. 审计与原始逻辑 ---
    # 排除审计路径和文件上传路径
    exclude_paths = [
        "/api/system/logs", 
        "/api/system/audit/logs",
        "/ws/"
    ]
    
    is_api = request.url.path.startswith("/api")
    # 使用 startswith 判断前缀，避免精确匹配导致子路径无法排除
    is_excluded = any(request.url.path.startswith(p) for p in exclude_paths)
    is_upload = "multipart/form-data" in request.headers.get("content-type", "")

    # 捕获请求体 (仅针对非 GET 且非上传、非排除路径的请求)
    payload_str = None
    if request.method != "GET" and is_api and not is_excluded and not is_upload:
        try:
            body = await request.body()
            if body:
                try:
                    payload_str = body.decode("utf-8")
                    # 重新包装 request 以允许下游继续读取 body
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
                except UnicodeDecodeError:
                    payload_str = "[Binary Data]"
        except Exception:
            pass
    
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    should_audit = is_api and not is_excluded

    if should_audit:
        # 执行脱敏处理
        masked_payload = payload_str
        if payload_str:
            try:
                payload_json = json.loads(payload_str)
                masked_json = await mask_sensitive_data(payload_json)
                masked_payload = json.dumps(masked_json, ensure_ascii=False)
            except:
                pass

        # 记录到 JSON 审计日志
        asyncio.create_task(add_audit_log(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            client_ip=request.client.host if request.client else "unknown",
            process_time=process_time,
            query_params=str(request.query_params),
            payload=masked_payload
        ))
        
        # 记录到控制台性能审计
        audit_log(f"API {request.method} {request.url.path}", process_time, [
            f"Status: {response.status_code}",
            f"Client: {request.client.host if request.client else 'unknown'}"
        ])
        
    return response

@app.on_event("startup")
async def startup_event():
    # 自动创建数据库表并执行自愈修复
    from app.utils.db_repair import init_db_with_repair
    await init_db_with_repair(engine)
    
    # 启动备份任务调度器
    from app.services.backup_service import BackupService
    asyncio.create_task(BackupService.start_scheduler())
    
    # 启动会话清理任务调度器
    from app.services.session_cleanup_service import SessionCleanupService
    asyncio.create_task(SessionCleanupService.start_scheduler())
    
    # 启动 Docker 自动更新调度器
    from app.services.docker_service import DockerService
    asyncio.create_task(DockerService.start_scheduler())
    
    # 启动 Telegram Bot 交互监听
    from app.services.telegram_bot_worker import TelegramBotWorker
    asyncio.create_task(TelegramBotWorker.start_all())
    
    # 初始化默认管理员
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                is_active=True
            )
            db.add(admin_user)
            await db.commit()
            logger.info("默认管理员账户已创建 (admin/admin123)")

    # 初始化系统默认配置 (优先从 config.json 加载)
    from app.core.config_manager import get_config
    current_json_config = get_config()
    
    # 初始化快捷命令
    from app.models.terminal import QuickCommand
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(QuickCommand))
        if not res.scalars().first():
            default_cmds = [
                {"title": "系统信息", "sort_order": 1, "command": "uname -snrmo"},
                {"title": "磁盘空间", "sort_order": 2, "command": "df -h"},
                {"title": "内存占用", "sort_order": 3, "command": "free -m"},
                {"title": "系统负载", "sort_order": 4, "command": "top"},
                {"title": "端口占用", "sort_order": 5, "command": "lsof -i -P -n | grep LISTEN"},
                {"title": "Docker 正在运行", "sort_order": 6, "command": "docker ps"},
                {"title": "Docker 资源占用", "sort_order": 7, "command": "docker stats --no-stream"},
                {"title": "Docker 清理虚悬镜像", "sort_order": 8, "command": "docker image prune -f"},
                {"title": "网络 IP 地址", "sort_order": 9, "command": "hostname -I"},
                {"title": "修改 root 密码", "sort_order": 10, "command": "passwd root"},
                {"title": "查看 SSH 配置", "sort_order": 11, "command": "cat /etc/ssh/sshd_config"},
                {"title": "编辑 SSH 配置", "sort_order": 12, "command": "vi /etc/ssh/sshd_config"},
                {"title": "重启 SSH 服务", "sort_order": 13, "command": "systemctl restart sshd || systemctl restart ssh"}
            ]
            for dc in default_cmds:
                db.add(QuickCommand(**dc))
            await db.commit()
            logger.info(f"已初始化 {len(default_cmds)} 条默认快捷命令")

    default_configs = [
        {"key": "audit_enabled", "value": "true", "description": "是否开启全局 API 审计日志"},
        {"key": "api_token", "value": "", "description": "外部 API 调用 Token"},
        {"key": "session_never_expire", "value": "false", "description": "会话永不过期（开启后会话不会自动过期）"}
    ]
    for cfg in default_configs:
        # 强制同步核心配置项：如果 config.json 里有，以 config.json 为准覆盖数据库
        if cfg["key"] in current_json_config and current_json_config[cfg["key"]]:
            val = current_json_config[cfg["key"]]
            await ConfigService.set(cfg["key"], val, cfg["description"])
        else:
            # 否则仅在数据库缺失时初始化
            current_val = await ConfigService.get(cfg["key"])
            if current_val is None:
                await ConfigService.set(cfg["key"], cfg["value"], cfg["description"])

    # 强制禁用 SSH 主机密钥检查


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("正在关闭服务...")
    logger.info("[系统] 服务已安全关闭。")

# WebSocket 实时日志
@app.websocket("/ws/system/logs")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # 验证 Token - 使用与 HTTP API 相同的验证逻辑
    from app.utils.auth import decode_access_token
    from app.services.config_service import ConfigService
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.user import User
    from app.services.session_service import get_session_by_id, update_session_activity
    from app.utils.time import get_local_time
    
    valid = False
    if token:
        # 检查静态 Token
        static_token = await ConfigService.get("api_token")
        if static_token and token == static_token:
            valid = True
        else:
            # 检查 JWT Token - 完整验证
            payload = decode_access_token(token)
            if payload and payload.get("type") != "2fa_pending":
                session_id = payload.get("sid")
                token_ps = payload.get("ps")
                
                if session_id and token_ps:
                    async with AsyncSessionLocal() as db:
                        session = await get_session_by_id(db, session_id)
                        if session:
                            # 检查会话是否已过期
                            now = get_local_time()
                            if now.tzinfo is not None:
                                now = now.replace(tzinfo=None)
                            
                            if session.expires_at >= now:
                                # 验证密码指纹
                                result = await db.execute(select(User).where(User.id == session.user_id))
                                user = result.scalars().first()
                                if user:
                                    current_ps = user.hashed_password[:16]
                                    if token_ps == current_ps:
                                        # 更新会话最后活动时间
                                        await update_session_activity(db, session_id)
                                        valid = True
    
    if not valid:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await websocket.accept()
    
    # 获取最近的历史日志并回填
    from app.utils.logger import get_last_n_logs, log_broadcaster
    history = get_last_n_logs(200) # 增加回填行数到 200
    for line in history:
        try:
            await websocket.send_text(line)
        except:
            return

    queue = log_broadcaster.subscribe()
    try:
        while True:
            # 获取队列中的新日志
            msg = await queue.get()
            try:
                await websocket.send_text(msg)
            except Exception:
                # 如果发送失败（连接已关），直接退出
                break
    except WebSocketDisconnect:
        pass
    finally:
        log_broadcaster.unsubscribe(queue)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
# ... (其他导入)

# 挂载图标目录
os.makedirs("/app/data/nav_icons", exist_ok=True)
os.makedirs("/app/data/nav_backgrounds", exist_ok=True)
app.mount("/nav_icons", StaticFiles(directory="/app/data/nav_icons"), name="nav_icons")
app.mount("/nav_backgrounds", StaticFiles(directory="/app/data/nav_backgrounds"), name="nav_backgrounds")

# 包含 API 路由
app.include_router(api_router, prefix="/api")

# --- 快捷图标路由 (解决第三方工具抓取失败问题) ---
@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
async def favicon():
    icon_path = os.path.join("./static", "favicon.svg")
    if os.path.exists(icon_path):
        return FileResponse(icon_path, media_type="image/svg+xml")
    return None

# 托管静态文件 (前端)
if os.path.exists("./static"):
    # 静态资源目录 (JS, CSS, Images)
    @app.get("/assets/{file_path:path}")
    async def serve_assets(file_path: str):
        file_full_path = os.path.join("./static/assets", file_path)
        if os.path.exists(file_full_path):
            return FileResponse(file_full_path)
        return None

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # 排除 API、图标和背景缓存路径
        if full_path.startswith("api") or full_path.startswith("nav_icons") or full_path.startswith("nav_backgrounds"):
            raise HTTPException(status_code=404)
        
        # 检查是否是具体的文件请求（比如 /vite.svg）
        file_path = os.path.join("./static", full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # SPA 路由兜底：返回 index.html
        index_path = os.path.join("./static", "index.html")
        return FileResponse(index_path)
else:
    @app.get("/")
    async def root():
        return {"message": "Lens API is running. Frontend static files not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=6565, reload=True)
