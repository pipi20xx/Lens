from fastapi import APIRouter, Query, Body
from typing import Dict, Any, Optional
from app.services.playback_report_service import PlaybackReportService
from app.utils.logger import logger

import re
import asyncio

router = APIRouter()

# --- image-proxy 进程内缓存 ---
_name_id_cache: Dict[str, Optional[str]] = {}   # { "剧名|类型": Emby ItemId 或 None }，None 也缓存避免反复打 Emby
_image_cache: Dict[str, tuple] = {}             # { cache_key: (bytes, content_type) }
_CACHE_MAX = 500

def _cache_put(store: dict, key, value):
    if len(store) >= _CACHE_MAX:
        store.clear()
    store[key] = value

# 限制同时打到 Emby 的请求数，避免整页海报同时请求挤爆 Emby
_search_semaphore = asyncio.Semaphore(8)

# 共享 HTTP 客户端（keep-alive 连接复用），配置与 EmbyService 一致：trust_env=False + 尊重 exclude_emby 代理排除
_image_http_client = None

def _get_emby_http_client():
    global _image_http_client
    if _image_http_client is None or _image_http_client.is_closed:
        from app.core.config_manager import get_config
        from app.utils.http_client import get_async_client
        proxy_cfg = get_config().get("proxy", {})
        use_proxy = not proxy_cfg.get("exclude_emby", True)
        _image_http_client = get_async_client(timeout=10.0, use_proxy=use_proxy)
    return _image_http_client

def _extract_series_name(raw: str) -> str:
    """播放记录标题为固定格式 '剧名 - s01e10 - 集标题'，取第一个 ' - ' 之前的部分即剧名"""
    return re.split(r"\s+-\s+", raw.strip(), maxsplit=1)[0].strip() or raw.strip()

async def _resolve_item_id(service, name: str, item_types: str) -> Optional[str]:
    """按剧名搜索 Emby ItemId：单次搜索直接取第一个结果（多版本重复项也取第一个）"""

    series_name = _extract_series_name(name)
    # 缓存 key 用剧名：同一部剧的不同集（s01e09/s01e10…）共享一次解析
    resolve_key = f"{series_name}|{item_types}"
    if resolve_key in _name_id_cache:
        return _name_id_cache[resolve_key]

    logger.info(f"🖼️ [报表图片] 解析剧名: '{name}' → '{series_name}'")
    actual_id = None
    try:
        async with _search_semaphore:
            resp = await _get_emby_http_client().get(f"{service.base_url}/Items", params={
                "api_key": service.api_key,
                "SearchTerm": series_name,
                "IncludeItemTypes": item_types,
                "Recursive": "true",
                "Limit": 1
            })
        items = resp.json().get("Items", []) if resp.status_code == 200 else []
        if items:
            actual_id = items[0].get("Id")
            logger.info(f"┗ ✅ [报表图片] '{series_name}' → ID: {actual_id} (Name: {items[0].get('Name')})")
        else:
            logger.info(f"┗ ❌ [报表图片] '{series_name}' Emby 无结果，返回 404")
    except Exception as e:
        # 超时/网络抖动属临时错误，不写缓存，下次请求重试
        logger.error(f"❌ [报表图片] 名称搜索异常(不缓存): {type(e).__name__}: {e}")
        return None

    _cache_put(_name_id_cache, resolve_key, actual_id)
    return actual_id

@router.get("/image-proxy", summary="图片代理")
async def image_proxy(item_id: Optional[str] = None, name: Optional[str] = None, type: str = "item"):
    from fastapi.responses import Response
    from app.services.emby import get_emby_service

    service = get_emby_service()
    if not service:
        return Response(status_code=404)

    image_type = "user" if type == "user" else "item"
    actual_id = item_id
    cache_key = f"{image_type}:{actual_id or name or ''}"

    # 1. 命中图片字节缓存直接返回
    if cache_key in _image_cache:
        data, ctype = _image_cache[cache_key]
        return Response(content=data, media_type=ctype,
                        headers={"Cache-Control": "public, max-age=86400"})

    # 2. 按名称搜索 ItemId（多候选 + 相似度匹配 + 解析缓存）
    if name and not actual_id:
        item_types = "Series" if type == "Series" else "Movie"
        actual_id = await _resolve_item_id(service, name, item_types)
        if actual_id:
            # 解析成功后按 ID 复用图片缓存：同一部剧不同集共享同一份海报
            cache_key = f"{image_type}:{actual_id}"

    if not actual_id:
        return Response(status_code=404)

    # 3. 请求 Emby 原生图片并缓存结果
    path = f"/Items/{actual_id}/Images/Primary" if image_type == "item" else f"/Users/{actual_id}/Images/Primary"
    url = f"{service.base_url}{path}"

    try:
        resp = await _get_emby_http_client().get(url, params={"api_key": service.api_key, "maxWidth": 400})
        if resp.status_code == 200 and resp.content:
            ctype = resp.headers.get("Content-Type", "image/jpeg")
            _cache_put(_image_cache, cache_key, (resp.content, ctype))
            return Response(content=resp.content, media_type=ctype,
                            headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        logger.error(f"❌ [报表图片] 获取图片异常(不缓存): {type(e).__name__}: {e}")

    return Response(status_code=404)

@router.get("/summary", summary="获取播放统计概览")
async def get_summary(days: int = Query(28, description="统计天数")):
    # 概览可以组合几个核心数据
    return {
        "user_activity": await PlaybackReportService.get_user_activity(days),
        "type_filters": await PlaybackReportService.get_type_filters()
    }

@router.get("/activity", summary="获取播放活跃度流水")
async def get_activity(days: int = Query(28, description="统计天数")):
    return await PlaybackReportService.get_user_activity(days)

@router.get("/users", summary="获取用户统计名单")
async def get_users():
    return await PlaybackReportService.get_user_list()

@router.get("/play-activity", summary="获取播放活跃度统计")
async def get_play_activity(
    item_type: str = Query("Episode", description="媒体类型"),
    days: int = Query(28, description="统计天数")
):
    return await PlaybackReportService.get_play_activity(item_type, days)

@router.get("/sessions", summary="获取会话列表")
async def get_sessions():
    return await PlaybackReportService.get_session_list()

@router.get("/config", summary="获取插件配置")
async def get_config():
    return await PlaybackReportService.get_plugin_config()

@router.post("/config", summary="更新插件配置")
async def update_config(config: Dict[str, Any] = Body(...)):
    return await PlaybackReportService.update_plugin_config(config)

@router.get("/users/{user_id}", summary="获取特定用户信息")
async def get_user_info(user_id: str):
    return await PlaybackReportService.get_user_info(user_id)

@router.get("/report-items", summary="获取报表项 (Get Items)")
async def get_report_items(parent_id: str = Query("0", description="父级ID")):
    return await PlaybackReportService.get_report_items(parent_id)

@router.get("/reports/{report_type}", summary="获取特定报表")
async def get_report(
    report_type: str,
    days: int = Query(28, description="统计天数"),
    user_id: Optional[str] = Query(None, description="用户ID")
):
    """
    report_type 可选: 
    MoviesReport (电影报表), 
    TvShowsReport (剧集报表), 
    DeviceName-BreakdownReport (设备统计), 
    PlaybackMethod-BreakdownReport (播放方式统计), 
    ItemType-BreakdownReport (媒体类型统计), 
    UserId-BreakdownReport (用户活跃统计), 
    HourlyReport (小时活跃度)
    """
    # 转换路径中的横杠为斜杠
    actual_report_type = report_type.replace("-", "/")
    return await PlaybackReportService.get_breakdown_report(actual_report_type, days, user_id)

@router.post("/query", summary="自定义 SQL 查询")
async def custom_query(query: str = Body(..., embed=True)):
    return await PlaybackReportService.submit_custom_query(query)

@router.get("/playlist", summary="获取用户播放清单统计")
async def get_playlist(days: int = Query(28, description="统计天数")):
    return await PlaybackReportService.get_user_playlist(days)

@router.get("/library-summary", summary="获取媒体库质量统计信息")
async def get_library_summary():
    return await PlaybackReportService.get_library_summary()

