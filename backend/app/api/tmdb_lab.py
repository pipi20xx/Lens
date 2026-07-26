import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from app.core.config_manager import get_config
from app.utils.http_client import get_async_client
from app.utils.logger import logger, audit_log
import time

router = APIRouter()

async def get_tmdb_config():
    config = get_config()
    tmdb_key = config.get("tmdb_api_key")
    if not tmdb_key:
        logger.error("❌ TMDB 操作失败: 未配置 TMDB API Key")
        raise HTTPException(status_code=400, detail="未配置 TMDB API Key")
    return tmdb_key

@router.get("/search", summary="TMDB 综合搜索")
async def search_tmdb(
    query: str = Query(..., description="搜索关键词"),
    media_type: str = Query("movie", description="媒体类型: movie 或 tv"),
    language: str = Query("zh-CN", description="语言"),
    page: int = Query(1, description="页码")
):
    start_time = time.time()
    tmdb_key = await get_tmdb_config()
    
    url = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {
        "api_key": tmdb_key,
        "query": query,
        "language": language,
        "page": page,
        "include_adult": "true"
    }

    logger.info(f"🔍 [TMDB Lab] 正在搜索 {media_type}: {query} (语言: {language})")
    
    try:
        async with get_async_client(use_proxy=True) as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"❌ TMDB 搜索失败: status={response.status_code}, body={response.text}")
                raise HTTPException(status_code=502, detail=f"TMDB API 返回错误 (HTTP {response.status_code}): {response.text[:200]}")
            
            data = response.json()
            audit_log("TMDB 搜索完成", (time.time() - start_time) * 1000, [
                f"查询: {query}",
                f"类型: {media_type}",
                f"语言: {language}",
                f"结果数: {len(data.get('results', []))}"
            ])
            return data
    except HTTPException:
        raise
    except httpx.ConnectError as e:
        logger.error(f"❌ TMDB 搜索连接失败: {type(e).__name__}: {str(e) or '无法连接到 TMDB 服务器，请检查网络代理配置'}")
        raise HTTPException(status_code=502, detail=f"无法连接到 TMDB 服务器，请检查网络代理配置: {str(e) or '连接超时或代理不可用'}")
    except httpx.TimeoutException as e:
        logger.error(f"❌ TMDB 搜索超时: {str(e)}")
        raise HTTPException(status_code=504, detail=f"TMDB API 请求超时: {str(e)}")
    except Exception as e:
        logger.error(f"❌ TMDB 搜索异常: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TMDB 搜索异常: {type(e).__name__}: {str(e) or '未知错误'}")

@router.get("/fetch", summary="TMDB 详情抓取 (原始数据)")
async def fetch_tmdb_details(
    tmdb_id: str = Query(..., description="TMDB ID"),
    media_type: str = Query("movie", description="媒体类型: movie 或 tv"),
    language: Optional[str] = Query(None, description="语言 (留空则不限制)"),
    include_translations: bool = Query(True, description="是否包含全语言翻译列表"),
    recursive: bool = Query(False, description="是否递归抓取所有季和集 (仅限 TV)")
):
    start_time = time.time()
    tmdb_key = await get_tmdb_config()
    
    # 构建追加字段
    append_items = ["credits", "images", "external_ids", "release_dates", "content_ratings", "keywords", "alternative_titles"]
    if include_translations:
        append_items.append("translations")
    
    append_to_response = ",".join(append_items)
    
    base_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"
    params = {
        "api_key": tmdb_key,
        "append_to_response": append_to_response
    }
    if language:
        params["language"] = language

    logger.info(f"🚀 [TMDB Lab] 抓取任务 ID: {tmdb_id} (全语言翻译: {include_translations}, 递归: {recursive})")
    
    try:
        async with get_async_client(use_proxy=True) as client:
            response = await client.get(base_url, params=params)
            if response.status_code != 200:
                logger.error(f"❌ TMDB 抓取失败: {response.text}")
                raise HTTPException(status_code=502, detail=f"TMDB API 返回错误: {response.text}")
            
            data = response.json()

            if media_type == "tv" and recursive and "seasons" in data:
                logger.info(f"┣ 📂 执行季/集深度递归抓取...")
                full_seasons = []
                for s_summary in data["seasons"]:
                    season_num = s_summary.get("season_number")
                    s_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_num}"
                    
                    s_append = ["credits", "images"]
                    if include_translations:
                        s_append.append("translations")
                        
                    s_params = {"api_key": tmdb_key, "append_to_response": ",".join(s_append)}
                    if language:
                        s_params["language"] = language
                    
                    s_resp = await client.get(s_url, params=s_params)
                    if s_resp.status_code == 200:
                        full_seasons.append(s_resp.json())
                    else:
                        full_seasons.append(s_summary)
                
                data["full_seasons_data"] = full_seasons

            return data

            audit_log("TMDB 详情抓取完成", (time.time() - start_time) * 1000, [
                f"ID: {tmdb_id}",
                f"类型: {media_type}",
                f"递归: {recursive}"
            ])
            return data
    except HTTPException:
        raise
    except httpx.ConnectError as e:
        logger.error(f"❌ TMDB 抓取连接失败: {type(e).__name__}: {str(e) or '无法连接到 TMDB 服务器'}")
        raise HTTPException(status_code=502, detail=f"无法连接到 TMDB 服务器，请检查网络代理配置: {str(e) or '连接超时或代理不可用'}")
    except httpx.TimeoutException as e:
        logger.error(f"❌ TMDB 抓取超时: {str(e)}")
        raise HTTPException(status_code=504, detail=f"TMDB API 请求超时: {str(e)}")
    except Exception as e:
        logger.error(f"❌ TMDB 抓取异常: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TMDB 抓取异常: {type(e).__name__}: {str(e) or '未知错误'}")

@router.get("/fetch-season", summary="TMDB 季详情深度抓取")
async def fetch_season_details(
    tmdb_id: str = Query(..., description="剧集 TMDB ID"),
    season_number: int = Query(..., description="季号"),
    language: Optional[str] = Query(None, description="语言"),
    include_translations: bool = Query(True, description="是否包含翻译")
):
    tmdb_key = await get_tmdb_config()
    append_items = ["credits", "images", "translations"] if include_translations else ["credits", "images"]
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}"
    params = {"api_key": tmdb_key, "append_to_response": ",".join(append_items)}
    if language: params["language"] = language
    try:
        async with get_async_client(use_proxy=True) as client:
            response = await client.get(url, params=params)
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch-episode", summary="TMDB 单集详情深度抓取")
async def fetch_episode_details(
    tmdb_id: str = Query(..., description="剧集 TMDB ID"),
    season_number: int = Query(..., description="季号"),
    episode_number: int = Query(..., description="集号"),
    language: Optional[str] = Query(None, description="语言"),
    include_translations: bool = Query(True, description="是否包含翻译")
):
    tmdb_key = await get_tmdb_config()
    
    append_items = ["credits", "images"]
    if include_translations:
        append_items.append("translations")
        
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}"
    params = {
        "api_key": tmdb_key,
        "append_to_response": ",".join(append_items)
    }
    if language:
        params["language"] = language

    try:
        async with get_async_client(use_proxy=True) as client:
            response = await client.get(url, params=params)
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
