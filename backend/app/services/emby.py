import httpx
import json
from typing import List, Dict, Any, Optional
from app.utils.logger import logger
from app.utils.http_client import get_async_client
from app.core.config_manager import get_config

class EmbyService:
    def __init__(self, url: str, api_key: str, user_id: str = None, tmdb_key: str = None):
        self.url = url.strip().rstrip('/')
        # 兼容性处理：如果用户填写的 URL 已经包含了 /emby，则不再重复添加
        if self.url.endswith('/emby'):
            self.base_url = self.url
            self.url = self.url[:-5] # 去掉 /emby 得到 root url
        else:
            self.base_url = f"{self.url}/emby"
            
        self.api_key = api_key.strip() if api_key else ""
        self.user_id = user_id.strip() if user_id else None
        self.tmdb_key = tmdb_key.strip() if tmdb_key else None
        self.headers = {
            "X-Emby-Token": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _get_client(self) -> httpx.AsyncClient:
        config = get_config()
        proxy_cfg = config.get("proxy", {})
        use_proxy = not proxy_cfg.get("exclude_emby", True)
        return get_async_client(timeout=30.0, headers=self.headers, use_proxy=use_proxy)

    async def _request(self, method: str, endpoint: str, params: Dict = None, json_data: Dict = None):
        """遵循 Emby 底层请求逻辑"""
        url = f"{self.base_url}{endpoint}"
        
        # 核心：必须在 URL 参数里带上 api_key
        full_params = {"api_key": self.api_key}
        if params:
            full_params.update(params)
            
        # 工业级透明调试
        logger.info(f"┃  ┣ 🚀 [API 执行] {method} {url}")
        if json_data:
            # 缩减 payload 显示，防止日志爆炸，但保留核心字段
            payload_peek = {k: v for k, v in json_data.items() if k in ["Genres", "GenreItems", "LockedFields", "LockData", "People"]}
            logger.info(f"┃  ┃  📦 Payload: {payload_peek}")

        try:
            async with self._get_client() as client:
                response = await client.request(method, url, params=full_params, json=json_data)
                res_text = response.text if response.text else "(No Content)"
                logger.info(f"┃  ┃  📥 [Emby 响应] Status: {response.status_code} | Body: {res_text[:200]}")
                return response
        except Exception as e:
            logger.error(f"┃  ┃  ❌ 指令发送异常 ({type(e).__name__}): {str(e)}")
            return None

    async def test_connection(self) -> Optional[Dict[str, Any]]:
        resp = await self._request("GET", "/System/Info")
        if resp is not None and resp.status_code == 200:
            return resp.json()
        return None

    async def fetch_items(self, item_types: List[str], recursive: bool = True, parent_id: str = None) -> List[Dict[str, Any]]:
        params = {
            "IncludeItemTypes": ",".join(item_types),
            "Recursive": str(recursive).lower(),
            "Fields": "Path,ProductionYear,ProviderIds,MediaStreams,DisplayTitle,SortName,Genres,GenreItems,LockedFields,LockData,People"
        }
        if parent_id:
            params["ParentId"] = parent_id
            
        resp = await self._request("GET", "/Items", params=params)
        return resp.json().get("Items", []) if resp and resp.status_code == 200 else []

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """获取单个项目的完整元数据 (强制全字段模式)"""
        full_fields = "ProviderIds,Name,Type,Id,Path,Overview,Genres,GenreItems,People,LockedFields,LockData,ChannelMappingInfo,MediaSources,MediaStreams"
        params = {"Fields": full_fields}
        try:
            async with self._get_client() as client:
                url = f"{self.url}/emby/Users/{self.user_id}/Items/{item_id}" if self.user_id else f"{self.url}/emby/Items/{item_id}"
                response = await client.get(url, params={**params, "api_key": self.api_key})
                return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"┃  ┃  ❌ 获取项目详情异常 ({type(e).__name__}): {str(e)}")
            return None

    async def update_item(self, item_id: str, data: Dict[str, Any]) -> bool:
        """严格按照原版发送 POST 更新"""
        resp = await self._request("POST", f"/Items/{item_id}", json_data=data)
        return resp is not None and resp.status_code in [200, 204]

    async def delete_item(self, item_id: str) -> bool:
        """调用 Emby API 删除条目"""
        resp = await self._request("DELETE", f"/Items/{item_id}")
        return resp is not None and resp.status_code in [200, 204]

def get_emby_service(server_id: str = None, emby_id: str = None) -> Optional[EmbyService]:
    """获取 EmbyService 实例。优先使用 server_id (本地 ID)，其次是 emby_id (Emby 真实 ID)。"""
    config = get_config()
    servers = config.get("emby_servers", [])
    
    # 查找目标服务器配置
    target_server = None
    if server_id:
        target_server = next((s for s in servers if s.get("id") == server_id), None)
    elif emby_id:
        target_server = next((s for s in servers if s.get("emby_id") == emby_id), None)
    else:
        active_id = config.get("active_server_id")
        target_server = next((s for s in servers if s.get("id") == active_id), None)
    
    # 如果没找到且列表不为空，默认用第一个（兜底）
    if not target_server and servers:
        target_server = servers[0]
        
    if not target_server:
        return None
        
    # 优先使用 api_key（永久密钥），避免 session_token 过期导致后台任务失败
    token = target_server.get("api_key") or target_server.get("session_token")
    return EmbyService(
        url=target_server.get("url", ""),
        api_key=token,
        user_id=target_server.get("user_id"),
        tmdb_key=config.get("tmdb_api_key")
    )
