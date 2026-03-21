import uuid
import re
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.session import Session
from app.models.user import User
from app.utils.time import get_local_time

def parse_user_agent(user_agent: str) -> dict:
    """解析 User-Agent 字符串，提取设备和浏览器信息"""
    result = {"device": "Unknown", "browser": "Unknown"}
    
    if not user_agent:
        return result
    
    ua_lower = user_agent.lower()
    
    # 检测操作系统/设备
    if "windows" in ua_lower:
        result["device"] = "Windows"
    elif "macintosh" in ua_lower or "mac os x" in ua_lower:
        result["device"] = "MacOS"
    elif "linux" in ua_lower and "android" not in ua_lower:
        result["device"] = "Linux"
    elif "android" in ua_lower:
        result["device"] = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower or "ipod" in ua_lower:
        result["device"] = "iOS"
    
    # 检测浏览器
    if "chrome" in ua_lower and "edg" not in ua_lower:
        result["browser"] = "Chrome"
    elif "edg" in ua_lower:
        result["browser"] = "Edge"
    elif "firefox" in ua_lower:
        result["browser"] = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        result["browser"] = "Safari"
    elif "opera" in ua_lower or "opr" in ua_lower:
        result["browser"] = "Opera"
    
    return result

async def create_session(
    db: AsyncSession,
    user: User,
    ip_address: str,
    user_agent: str,
    expires_hours: int = 24
) -> Session:
    """创建新的登录会话"""
    session_id = str(uuid.uuid4())
    device_info = parse_user_agent(user_agent)
    
    # 获取当前时间并转换为 offset-naive（SQLite 不支持时区）
    now = get_local_time()
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    
    # 检查是否开启永不过期配置
    from app.services.config_service import ConfigService
    never_expire = await ConfigService.get("session_never_expire", False)
    
    # 如果开启永不过期，设置过期时间为 100 年后
    if never_expire:
        expires_at = now + timedelta(days=365 * 100)
    else:
        expires_at = now + timedelta(hours=expires_hours)
    
    session = Session(
        user_id=user.id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
        device_info=device_info["device"],
        browser_info=device_info["browser"],
        login_time=now,
        last_activity=now,
        expires_at=expires_at,
        is_active=1
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return session

async def get_active_sessions(db: AsyncSession, user_id: int) -> list[Session]:
    """获取用户的所有活跃会话"""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id, Session.is_active == 1)
        .order_by(Session.login_time.desc())
    )
    return result.scalars().all()

async def get_session_by_id(db: AsyncSession, session_id: str) -> Session | None:
    """根据 session_id 获取会话"""
    result = await db.execute(
        select(Session)
        .where(Session.session_id == session_id, Session.is_active == 1)
    )
    return result.scalars().first()

async def update_session_activity(db: AsyncSession, session_id: str):
    """更新会话最后活动时间"""
    result = await db.execute(
        select(Session)
        .where(Session.session_id == session_id, Session.is_active == 1)
    )
    session = result.scalars().first()
    
    if session:
        # 获取当前时间并转换为 offset-naive（SQLite 不支持时区）
        now = get_local_time()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        
        # 检查会话是否已过期
        if session.expires_at < now:
            return
        
        session.last_activity = now
        await db.commit()

async def revoke_session(db: AsyncSession, session_id: str) -> bool:
    """撤销指定会话"""
    result = await db.execute(
        select(Session)
        .where(Session.session_id == session_id)
    )
    session = result.scalars().first()
    
    if session:
        session.is_active = 0
        await db.commit()
        return True
    return False

async def revoke_all_other_sessions(db: AsyncSession, user_id: int, exclude_session_id: str):
    """撤销用户的所有其他会话（保留当前会话）"""
    await db.execute(
        delete(Session)
        .where(
            Session.user_id == user_id,
            Session.session_id != exclude_session_id,
            Session.is_active == 1
        )
    )
    await db.commit()

async def cleanup_expired_sessions(db: AsyncSession):
    """清理过期会话"""
    now = get_local_time()
    # 处理时区问题：将当前时间转换为 offset-naive 用于数据库比较
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    
    await db.execute(
        delete(Session)
        .where(Session.expires_at < now)
    )
    await db.commit()
