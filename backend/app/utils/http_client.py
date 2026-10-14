import httpx
from typing import Optional, Dict, Any
from app.core.config_manager import get_config
from app.utils.logger import logger

def get_http_proxies() -> Optional[str]:
    """从配置中获取代理设置"""
    config = get_config()
    proxy_cfg = config.get("proxy", {})
    
    if not proxy_cfg.get("enabled") or not proxy_cfg.get("url"):
        return None
        
    return proxy_cfg["url"]

def get_async_client(timeout: float = 30.0, headers: Optional[Dict[str, str]] = None, use_proxy: bool = True, verify: bool = True) -> httpx.AsyncClient:
    """获取配置好的 AsyncClient

    verify=False 用于自签名证书的自建服务（如内网 Gitea）。
    """
    proxy_url = get_http_proxies() if use_proxy else None
    
    if proxy_url:
        logger.info(f"🌐 [网络代理] 当前请求将通过代理转发: {proxy_url}")
            
    return httpx.AsyncClient(
        timeout=timeout, 
        headers=headers, 
        proxies=proxy_url,
        trust_env=False,
        verify=verify,
        follow_redirects=True
    )
