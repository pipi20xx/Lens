import httpx
import json
from typing import List, Dict, Any, Optional
from app.utils.logger import logger
from app.utils.http_client import get_async_client
from app.core.config_manager import get_config

class EmbyUserService:
    def __init__(self, url: str, api_key: str):
        self.url = url.strip().rstrip('/')
        if self.url.endswith('/emby'):
            self.base_url = self.url
        else:
            self.base_url = f"{self.url}/emby"
            
        self.api_key = api_key.strip() if api_key else ""
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
        url = f"{self.base_url}{endpoint}"
        full_params = {"api_key": self.api_key}
        if params:
            full_params.update(params)
            
        try:
            async with self._get_client() as client:
                response = await client.request(method, url, params=full_params, json=json_data)
                return response
        except Exception as e:
            logger.error(f"Emby User API Error: {str(e)}")
            return None

    async def get_users(self) -> List[Dict[str, Any]]:
        resp = await self._request("GET", "/Users", params={"Public": "false"})
        return resp.json() if resp and resp.status_code == 200 else []

    async def create_user(self, name: str) -> Optional[Dict[str, Any]]:
        resp = await self._request("POST", "/Users/New", json_data={"Name": name})
        return resp.json() if resp and resp.status_code == 200 else None

    async def delete_user(self, user_id: str) -> bool:
        resp = await self._request("DELETE", f"/Users/{user_id}")
        return resp is not None and resp.status_code in [200, 204]

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        resp = await self._request("GET", f"/Users/{user_id}")
        return resp.json() if resp and resp.status_code == 200 else None

    async def update_user_policy(self, user_id: str, policy: Dict[str, Any]) -> bool:
        resp = await self._request("POST", f"/Users/{user_id}/Policy", json_data=policy)
        return resp is not None and resp.status_code in [200, 204]

    async def update_user_configuration(self, user_id: str, config: Dict[str, Any]) -> bool:
        resp = await self._request("POST", f"/Users/{user_id}/Configuration", json_data=config)
        return resp is not None and resp.status_code in [200, 204]

    async def update_user_password(self, user_id: str, new_password: str) -> bool:
        resp = await self._request("POST", f"/Users/{user_id}/Password", json_data={"NewPassword": new_password})
        return resp is not None and resp.status_code in [200, 204]

def get_emby_user_service(server_id: str = None) -> Optional[EmbyUserService]:
    config = get_config()
    servers = config.get("emby_servers", [])
    
    target_server = None
    if server_id:
        target_server = next((s for s in servers if s.get("id") == server_id), None)
    else:
        active_id = config.get("active_server_id")
        target_server = next((s for s in servers if s.get("id") == active_id), None)
    
    if not target_server and servers:
        target_server = servers[0]
        
    if not target_server:
        return None
        
    token = target_server.get("api_key") or target_server.get("session_token")
    return EmbyUserService(
        url=target_server.get("url", ""),
        api_key=token
    )