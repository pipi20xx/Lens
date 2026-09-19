"""统一 Telegram Bot API 客户端。

- 每个 bot token 复用一个长生命周期 httpx.AsyncClient，避免每次请求重建连接/TLS 握手
- 统一代理解析（全局 proxy 配置）、超时与重试（429 尊重 Retry-After，5xx 指数退避）
- sendMessage 解析失败自动降级为纯文本重发，保证消息必达
- 日志统一经 sanitize() 掩码，token 不落日志
"""
import asyncio
import re
from typing import Any, Dict, Optional

import httpx

from app.core.config_manager import get_config
from app.utils.logger import logger

API_BASE = "https://api.telegram.org"

# token 形如 123456789:AAxxxx...，出现在 URL 或错误信息中时统一掩码
_TOKEN_PATTERNS = [
    re.compile(r"bot(\d+):([A-Za-z0-9_-]+)"),
    re.compile(r"\b(\d{6,}):([A-Za-z0-9_-]{20,})\b"),
]


def sanitize(text: Any) -> str:
    """掩码文本中疑似 bot token 的片段，防止泄漏到日志。"""
    result = str(text)
    for pattern in _TOKEN_PATTERNS:
        result = pattern.sub(lambda m: f"{m.group(1)}:***", result)
    return result


class TelegramAPIError(Exception):
    """Telegram API 返回非 200 的业务异常。"""

    def __init__(self, status_code: int, description: str, retry_after: Optional[int] = None):
        self.status_code = status_code
        self.description = description
        self.retry_after = retry_after
        super().__init__(f"HTTP {status_code}: {description}")


def _resolve_proxy() -> Optional[str]:
    proxy_cfg = get_config().get("proxy", {})
    if proxy_cfg.get("enabled") and proxy_cfg.get("url"):
        return proxy_cfg.get("url")
    return None


class TelegramClient:
    """单个 bot 的 API 客户端，长生命周期复用连接。

    注意：项目当前锁定 httpx==0.25.1，代理参数名为 proxies（0.26+ 更名 proxy=）。
    """

    def __init__(self, token: str, timeout: float = 15.0):
        self.token = token
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._proxy_url: Optional[str] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        proxy_url = _resolve_proxy()
        if self._client is None or self._client.is_closed or proxy_url != self._proxy_url:
            await self.close()
            self._proxy_url = proxy_url
            self._client = httpx.AsyncClient(timeout=self._timeout, proxies=proxy_url)
        return self._client

    async def close(self):
        if self._client is not None and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception:
                pass
        self._client = None

    async def _request(
        self,
        method: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2,
    ) -> Any:
        url = f"{API_BASE}/bot{self.token}/{method}"
        client = await self._ensure_client()
        last_error = TelegramAPIError(0, "unreachable")

        for attempt in range(max_retries + 1):
            try:
                resp = await client.post(url, json=payload, params=params, timeout=timeout)
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                raise TelegramAPIError(0, sanitize(str(e))) from e

            if resp.status_code == 200:
                try:
                    return resp.json().get("result")
                except Exception:
                    return None

            try:
                body = resp.json()
            except Exception:
                body = {}
            description = body.get("description") or f"HTTP {resp.status_code}"
            retry_after = body.get("parameters", {}).get("retry_after")
            if retry_after is None:
                header = resp.headers.get("Retry-After")
                retry_after = int(header) if header and header.isdigit() else None
            error = TelegramAPIError(resp.status_code, sanitize(description), retry_after)

            if resp.status_code == 429 and attempt < max_retries:
                last_error = error
                await asyncio.sleep(error.retry_after or 3)
                continue
            if resp.status_code >= 500 and attempt < max_retries:
                last_error = error
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise error

        raise last_error

    # ---- Bot API 封装 ----

    async def get_me(self) -> Dict[str, Any]:
        return await self._request("getMe", max_retries=1)

    async def delete_webhook(self, drop_pending_updates: bool = False):
        return await self._request(
            "deleteWebhook",
            payload={"drop_pending_updates": drop_pending_updates},
            max_retries=1,
        )

    async def set_my_commands(self, commands: list):
        return await self._request("setMyCommands", payload={"commands": commands}, max_retries=1)

    async def get_updates(self, offset: Optional[int], poll_timeout: int = 30, drop_pending_updates: bool = False):
        params: Dict[str, Any] = {
            "timeout": poll_timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if drop_pending_updates:
            params["drop_pending_updates"] = True
        elif offset is not None:
            params["offset"] = offset
        # long polling 服务端最长持有 poll_timeout 秒，读取超时需大于它
        return await self._request(
            "getUpdates", params=params, timeout=poll_timeout + 5.0, max_retries=0
        )

    async def send_message(self, chat_id: Any, text: str, reply_markup: Optional[Dict] = None):
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            return await self._request("sendMessage", payload=payload, max_retries=2)
        except TelegramAPIError as e:
            if e.status_code == 400 and "parse entities" in e.description.lower():
                payload.pop("parse_mode", None)
                return await self._request("sendMessage", payload=payload, max_retries=0)
            raise

    async def edit_message(self, chat_id: Any, message_id: int, text: str, reply_markup: Optional[Dict] = None):
        """原地编辑已发送的消息（交互式菜单的核心，避免消息刷屏）。"""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            return await self._request("editMessageText", payload=payload, max_retries=1)
        except TelegramAPIError as e:
            description = e.description.lower()
            if "message is not modified" in description:
                # 内容与按钮完全一致（如连点刷新），视为成功
                return None
            if "parse entities" in description:
                payload.pop("parse_mode", None)
                return await self._request("editMessageText", payload=payload, max_retries=0)
            raise

    async def send_chat_action(self, chat_id: Any, action: str = "typing"):
        try:
            return await self._request(
                "sendChatAction",
                payload={"chat_id": chat_id, "action": action},
                max_retries=0,
            )
        except Exception:
            return None

    async def answer_callback_query(self, callback_query_id: Any, text: Optional[str] = None):
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            return await self._request("answerCallbackQuery", payload=payload, max_retries=1)
        except Exception as e:
            logger.warning(sanitize(f"⚠️ [TG] answerCallbackQuery 失败: {e}"))
            return None


_clients: Dict[str, TelegramClient] = {}


def get_client(token: str) -> TelegramClient:
    """按 token 获取（或创建）该 bot 的长生命周期客户端。"""
    client = _clients.get(token)
    if client is None:
        client = TelegramClient(token)
        _clients[token] = client
    return client


async def close_all_clients():
    for client in _clients.values():
        await client.close()
    _clients.clear()
