import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from app.core.config_manager import get_config, save_config
from app.schemas.notification import (
    NotificationBot,
    NotificationSettings,
    TestMessageRequest,
    TokenValidateRequest,
)
from app.services.notification_service import NotificationService
from app.services.telegram.formatting import b as tg_bold, esc as tg_esc
from app.services.telegram_bot_worker import TelegramBotWorker

router = APIRouter()

# 串行化通知设置的读改写，避免并发保存互相覆盖
_settings_lock = asyncio.Lock()

# 掩码标记：前端回传含此标记（或空）的 token 视为"未修改"，沿用已存 token
TOKEN_MASK = "••••••"


def mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 10:
        return f"{token[:2]}{TOKEN_MASK}"
    return f"{token[:6]}{TOKEN_MASK}{token[-4:]}"


def _is_masked(token: str) -> bool:
    return (not token) or (TOKEN_MASK in token)


async def _verify_interactive_token(token: str, bot_name: str):
    """开启交互模式且 token 有变更时先校验，失败则不落盘。"""
    ok, _, err = await TelegramBotWorker.verify_token(token)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"Bot '{bot_name}' Token 校验失败: {err or '无法连接 Telegram'}",
        )


@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings():
    config = get_config()
    settings = config.get("notification_settings", {"enabled": False, "bots": []})
    # token 脱敏返回，不回显明文
    masked_bots = []
    for bot in settings.get("bots", []):
        bot = dict(bot)
        bot["token"] = mask_token(bot.get("token", ""))
        masked_bots.append(bot)
    return {"enabled": settings.get("enabled", False), "bots": masked_bots}

@router.post("/settings")
async def save_notification_settings(settings: NotificationSettings):
    async with _settings_lock:
        config = get_config()
        existing = {
            b["id"]: b
            for b in config.get("notification_settings", {}).get("bots", [])
            if b.get("id")
        }
        new_bots = []
        for bot in settings.bots:
            item = bot.model_dump()
            old = existing.get(bot.id)
            if old:
                if _is_masked(item["token"]):
                    item["token"] = old.get("token", "")
            elif not item["token"]:
                raise HTTPException(status_code=400, detail=f"Bot '{bot.name}' 缺少 Token")
            new_bots.append(item)
        config["notification_settings"] = {"enabled": settings.enabled, "bots": new_bots}
        save_config(config)

    # 手动保存视为显式重启：丢弃积压消息，避免重放旧指令
    await TelegramBotWorker.start_all(drop_pending=True)
    return {"status": "success"}

@router.post("/bots")
async def add_bot(bot: NotificationBot):
    if not bot.token or _is_masked(bot.token):
        raise HTTPException(status_code=400, detail="缺少有效的 Bot Token")
    if bot.enabled and bot.is_interactive:
        await _verify_interactive_token(bot.token, bot.name)

    async with _settings_lock:
        config = get_config()
        settings = config.get("notification_settings", {"enabled": False, "bots": []})
        if not bot.id:
            bot.id = str(uuid.uuid4())
        settings["bots"].append(bot.model_dump())
        config["notification_settings"] = settings
        save_config(config)

    if bot.enabled and bot.is_interactive:
        await TelegramBotWorker.start_bot(bot.model_dump(), drop_pending=True)
    return bot

@router.put("/bots/{bot_id}")
async def update_bot(bot_id: str, bot: NotificationBot):
    async with _settings_lock:
        config = get_config()
        settings = config.get("notification_settings", {"enabled": False, "bots": []})
        bots = settings.get("bots", [])

        existing = next((b for b in bots if b["id"] == bot_id), None)
        if existing is None:
            raise HTTPException(status_code=404, detail="Bot not found")

        # token 为空或仍为掩码 => 未修改，沿用已存 token
        if _is_masked(bot.token):
            bot.token = existing.get("token", "")
        token_changed = bot.token != existing.get("token")

    # 校验放在锁外（涉及网络请求），失败则不落盘
    if bot.enabled and bot.is_interactive and token_changed:
        await _verify_interactive_token(bot.token, bot.name)

    async with _settings_lock:
        config = get_config()
        bots = config.get("notification_settings", {}).get("bots", [])
        for i, b in enumerate(bots):
            if b["id"] == bot_id:
                bots[i] = bot.model_dump()
                break
        else:
            raise HTTPException(status_code=404, detail="Bot not found")
        config["notification_settings"]["bots"] = bots
        save_config(config)

    if bot.enabled and bot.is_interactive:
        await TelegramBotWorker.start_bot(bot.model_dump(), drop_pending=True)
    else:
        await TelegramBotWorker.stop_bot(bot_id)
    return bot

@router.delete("/bots/{bot_id}")
async def delete_bot(bot_id: str):
    async with _settings_lock:
        config = get_config()
        settings = config.get("notification_settings", {"enabled": False, "bots": []})
        bots = settings.get("bots", [])
        settings["bots"] = [b for b in bots if b["id"] != bot_id]
        config["notification_settings"] = settings
        save_config(config)

    await TelegramBotWorker.stop_bot(bot_id)
    return {"status": "success"}

@router.get("/bots/{bot_id}/status")
async def get_bot_status(bot_id: str):
    """Bot 运行时状态（在线徽章数据源），不发网络请求。"""
    config = get_config()
    bot = next(
        (b for b in config.get("notification_settings", {}).get("bots", []) if b["id"] == bot_id),
        None,
    )
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    runtime = TelegramBotWorker.get_status(bot_id)
    interactive = bool(bot.get("enabled") and bot.get("is_interactive"))
    return {
        "enabled": bool(bot.get("enabled")),
        "interactive": interactive,
        "running": runtime["running"] if interactive else False,
        "username": runtime.get("username"),
        "error": runtime.get("error"),
    }

@router.post("/bots/validate")
async def validate_bot_token(req: TokenValidateRequest):
    """校验 Bot Token 有效性（getMe），供保存前校验。"""
    ok, username, err = await TelegramBotWorker.verify_token(req.token)
    return {"valid": ok, "username": username, "error": err}

@router.post("/test")
async def test_bot(req: TestMessageRequest):
    config = get_config()
    bot = next(
        (b for b in config.get("notification_settings", {}).get("bots", []) if b["id"] == req.bot_id),
        None,
    )
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    text = f"🔔 {tg_bold('测试通知')}\n\n{tg_esc(req.message)}"
    success, msg = await NotificationService.send_telegram_message(bot["token"], bot["chat_id"], text)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success"}
