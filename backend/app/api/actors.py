from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import httpx
import time
from app.db.session import get_db
from app.core.config_manager import get_config
from app.services.emby import EmbyService, get_emby_service
from app.utils.logger import logger, audit_log
from app.utils.http_client import get_async_client

router = APIRouter()

async def get_emby_context():
    service = get_emby_service()
    if not service:
        logger.error("❌ 任务终止: 未发现配置。请在系统设置中填入 IP 和 API Key")
        raise HTTPException(status_code=400, detail="未配置服务器")
    
    config = get_config()
    return service, config

async def fetch_tmdb_data(tmdb_key: str, path: str, params: Dict = None):
    if not tmdb_key:
        raise HTTPException(status_code=400, detail="未配置 TMDB API Key")
    url = f"https://api.themoviedb.org/3{path}"
    base_params = {"api_key": tmdb_key, "language": "zh-CN"}
    if params:
        base_params.update(params)
    async with get_async_client(timeout=20.0) as client:
        resp = await client.get(url, params=base_params)
        return resp.json() if resp.status_code == 200 else None

# --- 演员管理 API 实装 ---

@router.get("/search-emby", summary="从 Emby 库内搜索演员")
async def search_actor_in_emby(query: str = Query(...), db: AsyncSession = Depends(get_db)):
    """演员查找逻辑"""
    service, _ = await get_emby_context()
    start_time = time.time()
    
    if query.isdigit():
        logger.info(f"🚀 启动 [Emby 库内 TMDB ID 扫描]: {query}")
        all_actors = await service.fetch_items(["Person"], recursive=True)
        total = len(all_actors)
        results = []
        for i, actor_summary in enumerate(all_actors):
            aid = actor_summary["Id"]
            detail = await service.get_item(aid)
            if detail:
                tmdb_id = detail.get("ProviderIds", {}).get("Tmdb")
                if str(tmdb_id) == query:
                    logger.info(f"┃  ┣ ✅ 匹配成功: {detail.get('Name')} (Emby ID: {aid})")
                    results.append(detail)
                    break
            if i > 0 and i % 50 == 0:
                logger.info(f"┃  🕒 已扫描 {i}/{total} 个项目...")
    else:
        logger.info(f"🚀 启动 [Emby 名称模糊检索]: {query}")
        params = {"SearchTerm": query, "IncludeItemTypes": "Person", "Recursive": "true", "Fields": "Id"}
        resp = await service._request("GET", "/Items", params=params)
        summary_items = resp.json().get("Items", []) if resp else []
        results = []
        for it in summary_items[:20]:
            full_detail = await service.get_item(it["Id"])
            if full_detail:
                results.append(full_detail)
    
    logger.info(f"┗ ✅ Emby 演员检索完成 (耗时 {(time.time()-start_time):.2f}s, 命中数: {len(results)})")
    audit_log("Emby 检索结束", (time.time()-start_time)*1000, [f"命中数: {len(results)}"])
    return {"results": results}

@router.get("/search-tmdb", summary="从 TMDB 搜索演员")
async def search_actor_on_tmdb(query: str = Query(...), db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    _, config = await get_emby_context()
    tmdb_key = config.get("tmdb_api_key")
    logger.info(f"🚀 启动 [TMDB 演员搜索]: {query}")
    if query.isdigit():
        data = await fetch_tmdb_data(tmdb_key, f"/person/{query}")
        results = [data] if data else []
    else:
        data = await fetch_tmdb_data(tmdb_key, "/search/person", {"query": query})
        results = data.get("results", []) if data else []
    logger.info(f"┗ ✅ TMDB 演员搜索完成 (耗时 {time.time() - start_time:.2f}s, 命中数: {len(results)})")
    return {"results": results}

@router.post("/update-actor-name")
async def update_actor_name(
    emby_id: str = Body(..., embed=True),
    new_name: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    service, _ = await get_emby_context()
    start_time = time.time()
    actor_data = await service.get_item(emby_id)
    if not actor_data:
        raise HTTPException(status_code=404, detail="库内未找到该演员")
    old_name = actor_data.get('Name')
    logger.info(f"🚀 开始 [演员改名]: {old_name} → {new_name}")
    actor_data['Name'] = new_name
    success = await service.update_item(emby_id, actor_data)
    if success:
        logger.info(f"✅ 演员改名成功 (耗时 {time.time() - start_time:.2f}s, 旧名: {old_name}, 新名: {new_name})")
        audit_log("演员改名成功", (time.time()-start_time)*1000, [f"旧名: {old_name}", f"新名: {new_name}"])
        return {"message": "姓名更新成功"}
    raise HTTPException(status_code=500, detail="Emby API 提交失败")

@router.post("/update-emby-actor")
async def update_emby_actor(emby_id: str = Body(...), data: Dict = Body(...), db: AsyncSession = Depends(get_db)):
    service, _ = await get_emby_context()
    actor_data = await service.get_item(emby_id)
    if not actor_data:
        raise HTTPException(status_code=404, detail="演员不存在")
    logger.info(f"🚀 开始 [演员信息更新]: {actor_data.get('Name')} (Emby ID: {emby_id})")
    actor_data.update(data)
    success = await service.update_item(emby_id, actor_data)
    if success:
        logger.info(f"✅ 演员信息更新完成: {actor_data.get('Name')}")
    else:
        logger.error(f"❌ 演员信息更新失败: Emby API 提交失败 (Emby ID: {emby_id})")
    return {"success": success}
