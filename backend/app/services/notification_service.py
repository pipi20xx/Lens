"""通知服务：统一事件出口，按 Bot 订阅关系分发 Telegram 通知。

格式统一为 HTML（由 app.services.telegram.formatting 提供转义），
重试、代理解析、连接复用均由 app.services.telegram.client 统一承担。
"""
import asyncio
import threading
from typing import Tuple

from app.core.config_manager import get_config
from app.services.telegram.client import get_client
from app.services.telegram.formatting import b, esc
from app.utils.logger import logger


class NotificationService:
    @staticmethod
    async def send_telegram_message(token: str, chat_id: str, text: str) -> Tuple[bool, str]:
        """发送 Telegram 消息（text 为 HTML，解析失败会自动降级纯文本重发）。"""
        try:
            await get_client(token).send_message(chat_id, text)
            return True, "OK"
        except Exception as e:
            logger.error(f"❌ [Notification] TG 发送失败: {e}")
            return False, str(e)

    @classmethod
    async def emit(cls, event: str, title: str, message: str = ""):
        """
        触发通知事件 (乐高积木的核心出口)
        :param event: 事件名称，如 backup.success
        :param title: 通知标题
        :param message: 通知详情内容（纯文本，自动 HTML 转义）
        """
        config = get_config()
        settings = config.get("notification_settings", {})

        if not settings.get("enabled"):
            return

        bots = settings.get("bots", [])
        active_bots = [
            bot for bot in bots
            if bot.get("enabled") and bot.get("type") == "telegram"
            and (event in bot.get("subscribed_events", []) or "*" in bot.get("subscribed_events", []))
        ]

        if not active_bots:
            return

        logger.info(f"📢 [Notification] 正在为事件 '{event}' 分发通知给 {len(active_bots)} 个机器人...")
        formatted_text = f"{b(f'【{title}】')}\n\n{esc(message)}"

        results = await asyncio.gather(
            *(cls.send_telegram_message(bot.get("token"), bot.get("chat_id"), formatted_text) for bot in active_bots),
            return_exceptions=True,
        )
        for bot, result in zip(active_bots, results):
            if isinstance(result, Exception):
                logger.error(f"❌ [Notification] 事件 '{event}' 推送到 Bot '{bot.get('name')}' 异常: {result}")

    @classmethod
    def emit_sync(cls, event: str, title: str, message: str = ""):
        """同步上下文（线程池任务等无事件循环场景）的安全通知入口，非阻塞。"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cls.emit(event, title, message))
        except RuntimeError:
            threading.Thread(
                target=lambda: asyncio.run(cls.emit(event, title, message)),
                daemon=True,
            ).start()
