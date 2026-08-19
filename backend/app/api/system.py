from fastapi import APIRouter, Query, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import PlainTextResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.db.session import get_db
from app.models.config import SystemConfig
from app.schemas.system import BatchConfigUpdate, AuditLogListResponse, AuditLogResponse
from app.services.config_service import ConfigService
from app.utils.logger import get_log_dates, get_log_content, LOG_DIR, logger
from app.utils.http_client import get_async_client
from app.services.docker_service import DockerService
from app.core.config_manager import get_config
from datetime import datetime
import os
import secrets
import asyncio
import json

router = APIRouter()

CURRENT_VERSION = "v3.0.7"
DOCKER_IMAGE = "pipi20xx/lens"

@router.get("/version")
async def check_version():
    """检测 Docker Hub 上的最新版本"""
    # 统一处理本地版本号，移除可能存在的 v 前缀
    local_ver = CURRENT_VERSION.lstrip('v').strip()
    latest_version = local_ver
    has_update = False
    
    try:
        # 使用配置了代理的客户端
        url = f"https://hub.docker.com/v2/repositories/{DOCKER_IMAGE}/tags/?page_size=5&ordering=last_updated"
        async with get_async_client(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                tags = data.get("results", [])
                
                for tag in tags:
                    tag_name = tag.get("name")
                    if tag_name and tag_name != "latest":
                        # 统一移除远程版本号的 v 前缀进行比较
                        remote_ver = tag_name.lstrip('v').strip()
                        latest_version = remote_ver
                        
                        # 如果远程版本不等于本地版本
                        if remote_ver != local_ver:
                            # 简单的字符串大小比较或拆分比较
                            try:
                                remote_parts = [int(p) for p in remote_ver.split('.')]
                                local_parts = [int(p) for p in local_ver.split('.')]
                                if remote_parts > local_parts:
                                    has_update = True
                            except:
                                # 如果解析失败，回退到简单的非等比较
                                if remote_ver != local_ver:
                                    has_update = True
                        break
    except Exception:
        pass

    return {
        "current": f"v{local_ver}",
        "latest": f"v{latest_version}",
        "has_update": has_update,
        "docker_hub": f"https://hub.docker.com/r/{DOCKER_IMAGE}"
    }

@router.post("/upgrade")
async def upgrade_system(host_id: str = Query(None)):
    """一键系统升级：执行在被标记为 is_local 的宿主机上"""
    config = get_config()
    hosts = config.get("docker_hosts", [])
    
    target_host = None
    
    # 1. 寻找被用户手动标记为宿主机的节点
    if host_id:
        target_host = next((h for h in hosts if h.get("id") == host_id), None)
    else:
        # 寻找 is_local 为 True 的主机
        target_host = next((h for h in hosts if h.get("is_local") is True), None)

    if not target_host:
        raise HTTPException(
            status_code=400, 
            detail="升级中断：未找到标记为“宿主机”的连接。请在“Docker 容器管理”中编辑你的宿主机连接，并开启“宿主机标记”开关。"
        )

    try:
        service = DockerService(target_host)
        
        # 自动探测物理路径
        project_path = None
        
        # 1. 深度指纹探测：通过容器标签定位（这是 Compose 官方记录宿主机路径的标准方式）
        # 我们寻找镜像名包含 lens 且拥有 compose 工作目录标签的容器
        inspect_all_cmd = (
            "docker ps -a --format '{{.ID}}\t{{.Label \"com.docker.compose.project.working_dir\"}}\t{{.Image}}\t{{.Names}}'"
        )
        res_ps = service.exec_command(inspect_all_cmd, log_error=False)
        
        candidates = []
        if res_ps["success"] and res_ps["stdout"].strip():
            lines = res_ps["stdout"].strip().split('\n')
            for line in lines:
                parts = line.split('\t')
                if len(parts) < 3: continue
                cid, working_dir, image, name = parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else ""
                
                # 匹配特征：镜像名包含 lens，或者容器名包含 lens
                if DOCKER_IMAGE in image or "lens" in image.lower() or "lens" in name.lower():
                    # 如果有直接的 working_dir 标签，这是最准确的
                    if working_dir and working_dir != "<no value>":
                        project_path = working_dir
                        break
                    candidates.append(cid)

        # 2. 如果没有直接标签，尝试从匹配容器的挂载点反推
        if not project_path and candidates:
            for cid in candidates:
                inspect_cmd = f"docker inspect {cid} --format '{{{{json .Mounts}}}}'"
                res_insp = service.exec_command(inspect_cmd, log_error=False)
                if res_insp["success"]:
                    try:
                        import json
                        mounts = json.loads(res_insp["stdout"])
                        for m in mounts:
                            # 寻找关键挂载点 /app/data
                            if m.get("Destination") == "/app/data":
                                src = m.get("Source")
                                if src.endswith("/data"):
                                    project_path = src[:-5] # 移除末尾的 /data
                                else:
                                    project_path = os.path.dirname(src)
                                break
                        if project_path: break
                    except: pass

        # 3. 最后的保底策略：尝试传统的 docker compose ls
        if not project_path:
            detect_cmd = "docker compose ls --all --format json"
            res_compose = service.exec_command(detect_cmd, log_error=False)
            if res_compose["success"] and res_compose["stdout"].strip():
                try:
                    import json
                    projects = json.loads(res_compose["stdout"])
                    for p in projects:
                        p_name = str(p.get("Name") or p.get("Project", "")).lower()
                        if "lens" in p_name:
                            config_path = p.get("ConfigFiles") or p.get("ConfigPath")
                            if config_path:
                                project_path = os.path.dirname(config_path)
                                break
                except: pass

        if not project_path:
            project_path = target_host.get("project_path") or "/vol1/1000/NVME/Lens"
            logger.warning(f"⚠️ [系统升级] 路径探测失败，使用回退路径: {project_path}")
        else:
            logger.info(f"📍 [系统升级] 探测到项目路径: {project_path}")

        # 确保日志目录存在
        service.exec_command(f"mkdir -p {project_path}/data/logs")

        # 执行升级命令：纯 Docker Compose 升级流程
        # 适用于所有镜像部署用户
        upgrade_cmd = (
            f"nohup sh -c 'cd {project_path} && docker compose pull && docker compose up -d' "
            f"> {project_path}/data/logs/upgrade.log 2>&1 &"
        )
        
        logger.info(f"🚀 [系统升级] 用户已授权，正在通过宿主机 {target_host.get('name')} 执行后台升级...")
        res = service.exec_command(upgrade_cmd)
        
        if res["success"]:
            return {
                "message": f"升级任务已在宿主机 {target_host.get('name')} 上启动！系统正在拉取代码并重新构建，请稍后刷新页面。",
                "detected_path": project_path
            }
        else:
            raise HTTPException(status_code=500, detail=f"升级脚本启动失败: {res['stderr']}")
            
    except Exception as e:
        logger.error(f"❌ [系统升级] 发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/docs", include_in_schema=False)
async def get_documentation(request: Request, theme: str = "dark", token: str = None):
    referer = request.headers.get("referer")
    host = request.headers.get("host")
    
    # 允许 localhost 访问，或检查 referer
    if referer and host not in referer and "localhost" not in referer:
         raise HTTPException(status_code=403, detail="禁止直接访问 API 文档。请通过系统仪表盘进入。")
    
    # 兼容旧主题参数，映射到新系统
    theme_mapping = {
        "purple": "dark",
        "modern": "dark", 
        "oceanic": "dark",
        "crimson": "dark"
    }
    mode = theme_mapping.get(theme, theme)
    if mode not in ["light", "dark"]:
        mode = "dark"
    
    # 白天/夜晚模式配色方案
    theme_configs = {
        "dark": {
            "primary": "#a370f7",
            "bg": "#0f0913",
            "card": "#1a1021",
            "text": "#e2e2e9",
            "border": "rgba(255,255,255,0.1)",
            "input_bg": "#1a1021",
            "code_bg": "#111",
            "code_color": "#70ff70",
            "secondary_text": "rgba(255,255,255,0.6)",
            "hover_bg": "rgba(255,255,255,0.05)",
            "scrollbar": "rgba(255, 255, 255, 0.1)",
            "model_bg": "rgba(255,255,255,0.02)",
            "prop_type": "#f2a3ff",
            "invert_filter": "invert(1) brightness(2)"
        },
        "light": {
            "primary": "#7c3aed",
            "bg": "#f8f7fa",
            "card": "#ffffff",
            "text": "#1f2937",
            "border": "rgba(124, 58, 237, 0.15)",
            "input_bg": "#ffffff",
            "code_bg": "#f3f4f6",
            "code_color": "#059669",
            "secondary_text": "#6b7280",
            "hover_bg": "rgba(124, 58, 237, 0.06)",
            "scrollbar": "rgba(124, 58, 237, 0.2)",
            "model_bg": "rgba(124, 58, 237, 0.03)",
            "prop_type": "#7c3aed",
            "invert_filter": "none"
        }
    }
    
    cfg = theme_configs[mode]
    primary_color = cfg["primary"]
    bg_color = cfg["bg"]
    card_bg = cfg["card"]
    text_color = cfg["text"]
    border_color = cfg["border"]
    input_bg = cfg["input_bg"]
    code_bg = cfg["code_bg"]
    code_color = cfg["code_color"]
    secondary_text = cfg["secondary_text"]
    hover_bg = cfg["hover_bg"]
    scrollbar_color = cfg["scrollbar"]
    model_bg = cfg["model_bg"]
    prop_type_color = cfg["prop_type"]
    invert_filter = cfg["invert_filter"]

    # 自动授权脚本
    auth_js = ""
    if token:
        auth_js = f"""
        setTimeout(function() {{
            if (window.ui) {{
                window.ui.authActions.authorize({{
                    "BearerAuth": {{
                        name: "BearerAuth",
                        schema: {{
                            type: "http",
                            scheme: "bearer",
                            bearerFormat: "JWT"
                        }},
                        value: "{token}"
                    }}
                }});
                console.log("Lens：API Token 已自动注入");
            }}
        }}, 1000);
        """

    custom_css = f"""
    /* 基础背景与文字 */
    body {{ background-color: {bg_color} !important; margin: 0; padding: 0; }}
    .swagger-ui {{ background-color: {bg_color} !important; color: {text_color} !important; }}
    
    /* 滚动条美化 */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: {bg_color}; }}
    ::-webkit-scrollbar-thumb {{ background: {scrollbar_color}; border-radius: 10px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {primary_color}; }}
    
    /* Firefox 滚动条支持 */
    * {{ scrollbar-width: thin; scrollbar-color: {scrollbar_color} {bg_color}; }}

    .swagger-ui .topbar {{ display: none; }}
    .swagger-ui .info .title, .swagger-ui .info li, .swagger-ui .info p, .swagger-ui .info table, .swagger-ui .info h1, .swagger-ui .info h2, .swagger-ui .info h3 {{ color: {text_color} !important; }}
    
    /* 接口区块与标签 */
    .swagger-ui .opblock-tag {{ color: {text_color} !important; border-bottom: 1px solid {border_color} !important; }}
    .swagger-ui .opblock-tag:hover {{ background: {hover_bg} !important; }}
    .swagger-ui .opblock {{ background: {card_bg} !important; border: 1px solid {border_color} !important; box-shadow: none !important; }}
    .swagger-ui .opblock .opblock-summary-path {{ color: {text_color} !important; }}
    .swagger-ui .opblock .opblock-summary-description {{ color: {secondary_text} !important; }}
    
    /* 参数与请求配置区 */
    .swagger-ui .scheme-container {{ background: {card_bg} !important; box-shadow: none !important; border-top: 1px solid {border_color} !important; }}
    .swagger-ui select {{ background: {bg_color} !important; color: {text_color} !important; border-color: {border_color} !important; }}
    .swagger-ui input {{ background: {input_bg} !important; color: {text_color} !important; border: 1px solid {border_color} !important; }}
    .swagger-ui .btn {{ color: {text_color} !important; border-color: {border_color} !important; background: transparent !important; }}
    .swagger-ui .btn.execute {{ background-color: {primary_color} !important; border-color: {primary_color} !important; color: #fff !important; font-weight: bold !important; }}
    
    /* 重点：模型 (Models / Schemas) 区块 */
    .swagger-ui .models {{ background: {card_bg} !important; border: 1px solid {border_color} !important; margin: 20px !important; border-radius: 8px !important; }}
    .swagger-ui .models .model-container {{ background: transparent !important; margin: 0 !important; padding: 10px !important; }}
    .swagger-ui .models h4 {{ color: {text_color} !important; border-bottom: 1px solid {border_color} !important; padding-bottom: 10px !important; }}
    .swagger-ui .model-box {{ background: transparent !important; color: {text_color} !important; }}
    .swagger-ui .model-box-control {{ background: transparent !important; color: {text_color} !important; border: none !important; }}
    .swagger-ui .model-box-control:focus {{ outline: none !important; }}
    .swagger-ui .model-wrapper {{ background: transparent !important; }}
    .swagger-ui .model {{ color: {text_color} !important; background: transparent !important; }}
    .swagger-ui .model-title {{ color: {text_color} !important; }}
    .swagger-ui .prop-type {{ color: {prop_type_color} !important; }}
    .swagger-ui .prop-format {{ color: {secondary_text} !important; }}
    .swagger-ui .prop-name {{ color: {text_color} !important; font-weight: bold !important; }}
    
    /* 修复 Schemas 内部嵌套表格和列表的白底 */
    .swagger-ui section.models .model-container {{ background-color: transparent !important; }}
    .swagger-ui section.models .model-box {{ background-color: {model_bg} !important; }}
    .swagger-ui .model-toggle:after {{ filter: {invert_filter}; }}
    
    /* 响应与表格 */
    .swagger-ui table thead tr td, .swagger-ui table thead tr th {{ color: {text_color} !important; border-bottom: 1px solid {border_color} !important; }}
    .swagger-ui .response-col_status {{ color: {text_color} !important; }}
    .swagger-ui .parameter__name, .swagger-ui .parameter__type, .swagger-ui .parameter__deprecated, .swagger-ui .parameter__in {{ color: {text_color} !important; font-family: monospace !important; }}
    .swagger-ui .parameter__extension, .swagger-ui .parameter__in {{ font-style: italic !important; color: {secondary_text} !important; }}
    
    /* Parameters 专属修复 */
    .swagger-ui .opblock-section-header {{ background: {hover_bg} !important; border-top: 1px solid {border_color} !important; border-bottom: 1px solid {border_color} !important; }}
    .swagger-ui .opblock-section-header h4 {{ color: {text_color} !important; }}
    .swagger-ui .parameters-container, .swagger-ui .responses-container {{ background: transparent !important; }}
    .swagger-ui table.parameters, .swagger-ui table.responses-table {{ background: transparent !important; }}
    .swagger-ui .parameter__name {{ color: {primary_color} !important; font-weight: bold !important; }}
    .swagger-ui .parameter__type {{ color: {prop_type_color} !important; }}
    
    /* 按钮适配 */
    .swagger-ui .btn.try-out__btn {{ border-color: {primary_color} !important; color: {primary_color} !important; transition: all 0.3s !important; }}
    .swagger-ui .btn.try-out__btn:hover {{ background-color: {hover_bg} !important; }}
    .swagger-ui .btn.try-out__btn.cancel {{ border-color: #ff5252 !important; color: #ff5252 !important; }}
    
    /* 响应结果区 */
    .swagger-ui .responses-inner h4, .swagger-ui .responses-inner h5 {{ color: {text_color} !important; }}
    .swagger-ui .opblock-body pre {{ background: {code_bg} !important; color: {code_color} !important; border: 1px solid {border_color} !important; padding: 10px !important; border-radius: 8px !important; }}
    
    /* Markdown 描述 */
    .swagger-ui .renderedMarkdown p, .swagger-ui .renderedMarkdown li {{ color: {secondary_text} !important; }}

    /* 接口行右侧图标 (锁与箭头) 适配 */
    .swagger-ui .authorization__btn svg {{ fill: {primary_color} !important; }}
    .swagger-ui .opblock-summary-control svg {{ fill: {text_color} !important; opacity: 0.7; }}
    .swagger-ui .opblock-summary-control:hover svg {{ opacity: 1; }}
    .swagger-ui .view-line-link.copy-to-clipboard svg {{ fill: {text_color} !important; }}

    /* 重点：授权弹窗 (Available authorizations) 适配与位置修正 */
    .swagger-ui .scheme-container {{ position: relative !important; }}
    .swagger-ui .dialog-ux {{ 
      position: absolute !important; 
      top: 100% !important; 
      left: 50% !important; 
      transform: translateX(-50%) !important; 
      z-index: 9999 !important;
      width: 600px !important; 
    }}
    .swagger-ui .modal-ux-mask {{ 
      position: absolute !important; 
      top: 0 !important; 
      left: 0 !important; 
      width: 100% !important; 
      height: 10000px !important; 
      z-index: 9998 !important; 
      background: rgba(0, 0, 0, 0.5) !important; 
    }}
    .swagger-ui .modal-ux {{
      background-color: {card_bg} !important; 
      border: 1px solid {border_color} !important;
      border-radius: 8px !important;
      max-height: 700px !important; 
      overflow-y: auto !important; 
      box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
    }}
    .swagger-ui .modal-ux-header {{ border-bottom: 1px solid {border_color} !important; padding: 10px 15px !important; }}
    .swagger-ui .modal-ux-header h3 {{ color: {text_color} !important; }}
    .swagger-ui .modal-ux-content {{ background-color: {bg_color} !important; padding: 15px !important; }}
    .swagger-ui .modal-ux-content h4 {{ color: {text_color} !important; }}
    .swagger-ui .auth-container {{ color: {text_color} !important; border-bottom: 1px solid {border_color} !important; padding: 15px 0 !important; }}
    .swagger-ui .auth-container:last-of-type {{ border-bottom: none !important; }}
    .swagger-ui .auth-container label {{ color: {text_color} !important; }}
    .swagger-ui .auth-btn-wrapper {{ justify-content: center !important; gap: 10px !important; }}
    .swagger-ui .modal-ux-content p {{ color: {secondary_text} !important; }}
    
    /* 适配新版 JSON Schema 渲染器 */
    .json-schema-2020-12-accordion {{ background: transparent !important; border: none !important; color: {text_color} !important; }}
    .json-schema-2020-12-accordion__children {{ color: {text_color} !important; }}
    .json-schema-2020-12__title {{ color: {text_color} !important; font-weight: bold !important; }}
    .json-schema-2020-12-accordion__icon svg {{ fill: {text_color} !important; }}
    .json-schema-2020-12-accordion:hover {{ background: {hover_bg} !important; }}
    .json-schema-2020-12-expand-deep-button {{ 
      color: {primary_color} !important; 
      background: transparent !important; 
      border: 1px solid {primary_color} !important; 
      border-radius: 4px !important;
      padding: 2px 8px !important;
      cursor: pointer !important;
      font-size: 12px !important;
    }}
    .json-schema-2020-12-expand-deep-button:hover {{ 
      background: {primary_color} !important; 
      color: #fff !important; 
    }}
    """
    
    from fastapi.openapi.docs import get_swagger_ui_html
    response = get_swagger_ui_html(
        openapi_url="/api/system/openapi.json", 
        title="Lens API Documentation"
    )
    
    html_content = response.body.decode("utf-8")
    custom_injection = f"<style>{custom_css}</style><script>{auth_js}</script>"
    new_content = html_content.replace("</head>", f"{custom_injection}</head>")
    
    return HTMLResponse(content=new_content)

@router.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(request: Request):
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(title="Lens API", version=CURRENT_VERSION, routes=request.app.routes)
    
    # 1. 注入全局安全定义
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # 2. 强制遍历所有路径，确保每个操作都明确引用 BearerAuth
    # 这一步能解决点击锁图标后弹窗可能为空的问题
    if "paths" in schema:
        for path in schema["paths"].values():
            for operation in path.values():
                operation["security"] = [{"BearerAuth": []}]

    # 3. 设置全局安全校验
    schema["security"] = [{"BearerAuth": []}]
    return schema

@router.get("/config", summary="获取所有系统配置")
async def get_all_configs(db: AsyncSession = Depends(get_db)):
    # 1. 获取数据库中的所有配置项
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    res = {}
    for c in configs:
        val = c.value
        # 智能解析 JSON 字符串 (列表或字典)
        if isinstance(val, str):
            if (val.startswith("[") and val.endswith("]")) or (val.startswith("{") and val.endswith("}")):
                try:
                    import json
                    val = json.loads(val)
                except:
                    pass
            elif val.lower() == "true": val = True
            elif val.lower() == "false": val = False
            
        res[c.key] = val
    
    # 2. 确保关键配置项（如 api_token）通过 ConfigService 获取（包含 config.json 的回退逻辑）
    keys_to_ensure = [
        "api_token", "auth_enabled", "audit_enabled",
        "ai_provider", "ai_api_key", "ai_base_url", "ai_model", "ai_bookmark_categories",
        "ai_use_proxy"
    ]
    for key in keys_to_ensure:
        if key not in res or not res[key]:
            res[key] = await ConfigService.get(key)
            
    return res

@router.post("/config", summary="批量更新系统配置")
async def update_configs(update: BatchConfigUpdate):
    for cfg in update.configs:
        await ConfigService.set(cfg.key, cfg.value, cfg.description)
    return {"message": "配置已更新"}

@router.post("/token/generate", summary="生成随机 API Token")
async def generate_token():
    token = secrets.token_urlsafe(32)
    return {"token": token}

@router.get("/audit/logs", response_model=AuditLogListResponse, summary="查询审计日志")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    from app.utils.audit import audit_buffer
    total = len(audit_buffer)
    start = (page - 1) * page_size
    end = start + page_size
    items = audit_buffer[start:end]
    return {"total": total, "items": items}

@router.get("/logs/dates")
async def fetch_log_dates():
    return get_log_dates()

@router.get("/logs/content/{date}")

async def fetch_log_content(date: str):

    # 返回原始顺序，由前端 LogConsole 处理反转

    return {"content": get_log_content(date)}



@router.get("/logs/raw", response_class=PlainTextResponse)

async def fetch_raw_log(type: str = Query("monitor")):

    """日志接口：返回当前最新的原始文本日志 (倒序，最新在上)"""

    current_date = datetime.now().strftime("%Y-%m-%d")

    content = get_log_content(current_date)

    lines = content.splitlines()

    lines.reverse()

    return "\n".join(lines)



@router.get("/logs/export/{date}", response_class=PlainTextResponse)

async def export_log_by_date(date: str):

    """按日期返回原始文本日志 (倒序，最新在上)"""

    content = get_log_content(date)

    lines = content.splitlines()

    lines.reverse()

    return "\n".join(lines)



@router.get("/config/export", summary="导出全局配置")
async def export_config():
    """导出 config.json"""
    config = get_config()
    # 返回格式化的 JSON
    return PlainTextResponse(
        json.dumps(config, indent=4, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=lens_config_{datetime.now().strftime('%Y%m%d')}.json"}
    )

@router.post("/config/import", summary="导入全局配置")
async def import_config(file: UploadFile = File(...)):
    """导入并覆盖 config.json"""
    try:
        content = await file.read()
        raw_config = json.loads(content)
        
        if not isinstance(raw_config, dict):
            raise HTTPException(status_code=400, detail="无效的配置文件格式")
            
        from app.core.config_manager import save_config, normalize_config
        
        # 使用标准化逻辑处理导入的配置，确保兼容性和完整性
        new_config = normalize_config(raw_config)
        save_config(new_config)
        
        # 同步更新数据库配置，确保 ConfigService 优先读取新导入的值
        for key, value in new_config.items():
            if isinstance(value, (str, int, float, bool, list)):
                await ConfigService.set(key, value)
        
        # 强制刷新配置缓存
        await ConfigService.refresh_cache()
        
        # 触发关键服务的重载
        from app.services.backup_service import BackupService
        await BackupService.reload_tasks()
        
        return {"message": "配置已导入，并已执行兼容性检查与服务重载"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON 解析失败")
    except Exception as e:
        logger.error(f"导入配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


