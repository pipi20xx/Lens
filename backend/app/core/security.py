"""API 鉴权统一入口。

HTTP 中间件（main.py）与 WebSocket 端点共用 verify_request_token，
校验链：静态 API Token → JWT → 会话存在/未过期 → 密码指纹。
"""
from sqlalchemy import select

from app.models.user import User
from app.utils.auth import decode_access_token


async def verify_request_token(token: str) -> bool:
    """校验请求携带的 token 是否有效。"""
    if not token:
        return False

    # 1. 静态 Token（外部调用）
    from app.services.config_service import ConfigService
    static_token = await ConfigService.get("api_token")
    if static_token and token == static_token:
        return True

    # 2. JWT Token（登录会话）
    from app.db.session import AsyncSessionLocal
    from app.services.session_service import get_session_by_id, update_session_activity
    from app.utils.time import get_local_time

    payload = decode_access_token(token)
    if not payload or payload.get("type") == "2fa_pending":
        return False

    session_id = payload.get("sid")
    token_ps = payload.get("ps")
    if not session_id or not token_ps:
        return False

    async with AsyncSessionLocal() as db:
        session = await get_session_by_id(db, session_id)
        if not session:
            return False

        now = get_local_time()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        if session.expires_at < now:
            return False

        result = await db.execute(select(User).where(User.id == session.user_id))
        user = result.scalars().first()
        if not user or token_ps != user.hashed_password[:16]:
            return False

        await update_session_activity(db, session_id)
        return True
