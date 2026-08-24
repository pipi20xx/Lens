"""
外观壁纸代理 API
- 代理外部壁纸图片，解决 WebGL CORS 限制
"""
import os
import time
import hashlib
import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

logger = logging.getLogger(__name__)
router = APIRouter()

WALLPAPER_CACHE_DIR = os.path.join("/app/data", "tmp", "wallpaper")

# 已知的随机壁纸 API 域名 —— URL 不变但每次请求返回不同图片
# 对这类源使用短时间缓存（30 秒），保证同一次页面加载中多个请求
# （CSS 背景、<img>、WebGL 纹理、tone 分析）拿到同一张图片
RANDOM_WALLPAPER_DOMAINS = {
    "loliapi.com",
    "www.loliapi.com",
    "api.loliapi.com",
    "random.iisu.cn",
    "api.dujin.org",
    "img.xjh.me",
    "random.52ecy.cn",
}

# 随机壁纸的短缓存时间（秒）
RANDOM_WALLPAPER_CACHE_TTL = 30
# 固定壁纸的长缓存时间（秒）
FIXED_WALLPAPER_CACHE_TTL = 3600


def _is_random_wallpaper_url(url: str) -> bool:
    """判断 URL 是否指向随机壁纸 API"""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).hostname or ""
        return host.lower() in RANDOM_WALLPAPER_DOMAINS
    except Exception:
        return False


def _ensure_wallpaper_dir():
    os.makedirs(WALLPAPER_CACHE_DIR, exist_ok=True)


def _is_valid_image(data: bytes) -> bool:
    """校验数据是否为有效图片"""
    if not data or len(data) < 16:
        return False
    if data[:3] == b'\xff\xd8\xff':  # JPEG
        return True
    if data[:8] == b'\x89PNG\r\n\x1a\n':  # PNG
        return True
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':  # WebP
        return True
    if data[:6] in (b'GIF87a', b'GIF89a'):  # GIF
        return True
    return False


@router.get("/wallpaper_proxy")
async def proxy_wallpaper(
    url: str = Query("", description="要代理的壁纸 URL，为空时使用默认 loliapi 地址"),
    refresh: bool = Query(False, description="强制刷新（跳过缓存）"),
):
    """
    代理外部壁纸图片，解决 WebGL CORS 限制。
    不传 url 时默认使用 https://www.loliapi.com/acg/pc/

    缓存策略：
    - 随机壁纸 API（如 loliapi.com）：短缓存 30 秒
    - 固定 URL 壁纸：长缓存 1 小时
    - refresh=True 可强制跳过缓存
    """
    target_url = url.strip() if url.strip() else "https://www.loliapi.com/acg/pc/"
    if not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="无效的 URL")

    is_random = _is_random_wallpaper_url(target_url)
    cache_ttl = RANDOM_WALLPAPER_CACHE_TTL if is_random else FIXED_WALLPAPER_CACHE_TTL
    skip_cache = refresh

    # 使用 URL hash 作为缓存 key
    url_hash = hashlib.md5(target_url.encode()).hexdigest()

    # 尝试读取缓存
    cached_files = []
    if not skip_cache:
        try:
            for f in os.listdir(WALLPAPER_CACHE_DIR):
                if f.startswith(url_hash):
                    cached_files.append(f)
        except FileNotFoundError:
            pass

        # 如果有缓存且未过期，直接返回
        if cached_files:
            cached_file = os.path.join(WALLPAPER_CACHE_DIR, cached_files[0])
            try:
                stat = os.stat(cached_file)
                age = time.time() - stat.st_mtime
                if age < cache_ttl:
                    def _read_cache():
                        with open(cached_file, "rb") as f:
                            return f.read()
                    cached = await asyncio.to_thread(_read_cache)
                    if cached and _is_valid_image(cached):
                        # 推断 content-type
                        ext = os.path.splitext(cached_files[0])[1].lower()
                        ct = {
                            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                            ".png": "image/png", ".webp": "image/webp",
                            ".gif": "image/gif",
                        }.get(ext, "image/jpeg")
                        return Response(
                            content=cached,
                            media_type=ct,
                            headers={
                                "Cache-Control": f"public, max-age={cache_ttl}",
                                "Access-Control-Allow-Origin": "*",
                            },
                        )
            except (OSError, IOError):
                pass

    # 下载新图片
    await asyncio.to_thread(_ensure_wallpaper_dir)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200 and _is_valid_image(resp.content):
                content_type = resp.headers.get("content-type", "image/jpeg")
                ext_map = {
                    "image/jpeg": ".jpg", "image/png": ".png",
                    "image/webp": ".webp", "image/gif": ".gif",
                }
                ext = ext_map.get(content_type, ".jpg")

                # 写入缓存
                cache_filename = f"{url_hash}{ext}"
                cache_filepath = os.path.join(WALLPAPER_CACHE_DIR, cache_filename)

                # 清理同 hash 的旧缓存
                for old in cached_files:
                    try:
                        os.remove(os.path.join(WALLPAPER_CACHE_DIR, old))
                    except OSError:
                        pass

                def _write():
                    with open(cache_filepath, "wb") as f:
                        f.write(resp.content)
                await asyncio.to_thread(_write)

                return Response(
                    content=resp.content,
                    media_type=content_type,
                    headers={
                        "Cache-Control": f"public, max-age={cache_ttl}",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            else:
                raise HTTPException(status_code=502, detail="壁纸源返回无效数据")
    except httpx.RequestError as e:
        logger.warning(f"壁纸代理请求失败: {e}")
        raise HTTPException(status_code=502, detail=f"壁纸代理失败: {str(e)}")
