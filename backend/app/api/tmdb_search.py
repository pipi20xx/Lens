from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.db.session import get_db
from app.core.config_manager import get_config
from app.services.emby import EmbyService, get_emby_service
from app.utils.logger import logger, audit_log
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
import time

router = APIRouter()

class TmdbSearchRequest(BaseModel):
    tmdb_id: str
    search_movies: bool = True
    search_series: bool = True
    show_raw_json: bool = False

class TmdbSearchResponse(BaseModel):
    results: List[Dict[str, Any]]

FULL_FIELDS = "ProviderIds,Name,Type,Id,Path,Overview,ProductionYear,CommunityRating,OfficialRating,Genres,Studios,PremiereDate,EndDate,Status,RunTimeTicks,Taglines,UserData,SeriesName,SeasonName,IndexNumber,ParentIndexNumber,ParentId,MediaStreams,MediaSources,People,ExternalUrls"

# --- 使用 config.json 还原被误删的核心辅助函数 ---
async def get_active_emby():
    service = get_emby_service()
    if not service: 
        logger.error("❌ 任务终止: 未发现配置。请在系统设置中填入 IP 和 API Key")
        raise HTTPException(status_code=400, detail="未配置服务器")
    return service

async def _fetch_series_structure(service: EmbyService, series_item: Dict[str, Any]) -> Dict[str, Any]:
    series_details = series_item.copy()
    series_details["Seasons"] = []
    logger.info(f"┃  ┣ 📂 正在解析剧集层级: {series_item.get('Name')}")
    
    params = {"Fields": FULL_FIELDS, "IncludeItemTypes": "Season", "Recursive": "false", "ParentId": series_item["Id"]}
    resp = await service._request("GET", "/Items", params=params)
    seasons = resp.json().get("Items", []) if resp else []

    for s_item in seasons:
        season_details = s_item.copy()
        logger.info(f"┃  ┃  ┣ 📅 正在拉取: {s_item.get('Name')}...")
        ep_params = {"Fields": FULL_FIELDS, "IncludeItemTypes": "Episode", "Recursive": "false", "ParentId": s_item["Id"]}
        ep_resp = await service._request("GET", "/Items", params=ep_params)
        eps = ep_resp.json().get("Items", []) if ep_resp else []
        logger.info(f"┃  ┃  ┃  ┗ 找到 {len(eps)} 集数据")
        season_details["Episodes"] = eps
        series_details["Seasons"].append(season_details)
    return series_details

@router.post("/search-by-id", response_model=TmdbSearchResponse)
async def search_by_tmdb_id(request: TmdbSearchRequest, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    logger.info(f"🚀 启动 [TMDB ID 深度搜索] 任务: {request.tmdb_id}")

    # 使用还原后的辅助函数
    service = await get_active_emby()
    
    include_types = []
    if request.search_movies: include_types.append("Movie")
    if request.search_series: include_types.append("Series")
    
    final_results = []
    logger.info(f"┣ 🔍 正在执行全库扫描 (Types: {include_types})...")

    params = {"Fields": FULL_FIELDS, "Recursive": "true", "IncludeItemTypes": ",".join(include_types)}
    resp = await service._request("GET", "/Items", params=params)
    all_items = resp.json().get("Items", []) if resp else []
    
    for it in all_items:
        p_ids = it.get('ProviderIds', {})
        if str(p_ids.get('Tmdb')) == request.tmdb_id.strip():
            logger.info(f"┃  ┣ ✅ 匹配成功: {it.get('Name')}")
            if it["Type"] == "Series":
                it = await _fetch_series_structure(service, it)
            final_results.append(it)

    elapsed = (time.time()-start_time)
    logger.info(f"┗ ✅ 深度搜索完成 (耗时 {elapsed:.2f}s, 匹配项目数: {len(final_results)})")
    audit_log("深度搜索任务完成", elapsed*1000, [
        f"TMDB ID: {request.tmdb_id}",
        f"匹配项目数: {len(final_results)}"
    ])
    return TmdbSearchResponse(results=final_results)
