from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.session import Session
from app.utils.auth import get_current_user
from app.services.session_service import (
    get_active_sessions,
    revoke_session,
    revoke_all_other_sessions
)
from app.utils.audit import add_audit_log
import asyncio

router = APIRouter()

@router.get("/sessions", summary="获取当前用户的所有活跃会话")
async def get_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的所有活跃会话"""
    sessions = await get_active_sessions(db, current_user.id)
    
    # 获取当前会话的 session_id
    from app.utils.auth import decode_access_token
    auth_header = request.headers.get("Authorization")
    current_session_id = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        payload = decode_access_token(token)
        if payload:
            current_session_id = payload.get("sid")
    
    # 格式化返回数据
    result = []
    for session in sessions:
        is_current = session.session_id == current_session_id
        
        # 计算过期时间
        from app.utils.time import get_local_time
        from datetime import timedelta
        now = get_local_time()
        
        # 将 offset-aware 的当前时间转换为 offset-naive 用于比较（SQLite 不支持时区）
        if now.tzinfo is not None:
            now_naive = now.replace(tzinfo=None)
        else:
            now_naive = now
        
        if session.expires_at > now_naive:
            hours_left = int((session.expires_at - now_naive).total_seconds() / 3600)
            expires_text = f"{hours_left}小时后过期"
        else:
            expires_text = "已过期"
        
        result.append({
            "id": session.id,
            "session_id": session.session_id,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "device_info": f"{session.device_info} / {session.browser_info}",
            "login_time": session.login_time.strftime("%Y-%m-%d %H:%M:%S") if session.login_time else None,
            "last_activity": session.last_activity.strftime("%Y-%m-%d %H:%M:%S") if session.last_activity else None,
            "expires_text": expires_text,
            "is_current": is_current
        })
    
    return {"sessions": result}

@router.delete("/sessions/{session_id}", summary="撤销指定会话")
async def revoke_user_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤销指定的会话（不能撤销当前会话）"""
    # 获取当前会话的 session_id
    from app.utils.auth import decode_access_token
    auth_header = request.headers.get("Authorization")
    current_session_id = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        payload = decode_access_token(token)
        if payload:
            current_session_id = payload.get("sid")
    
    # 不能撤销当前会话
    if session_id == current_session_id:
        raise HTTPException(status_code=400, detail="不能撤销当前会话")
    
    # 检查会话是否属于当前用户
    from sqlalchemy import select
    result = await db.execute(
        select(Session)
        .where(Session.session_id == session_id, Session.user_id == current_user.id)
    )
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 撤销会话
    success = await revoke_session(db, session_id)
    
    if success:
        client_ip = request.client.host if request.client else "unknown"
        asyncio.create_task(add_audit_log(
            "DELETE",
            f"/api/auth/sessions/{session_id}",
            200,
            client_ip,
            0,
            payload=f"用户 {current_user.username} 撤销会话 {session_id}"
        ))
        return {"message": "会话已撤销"}
    
    raise HTTPException(status_code=500, detail="撤销会话失败")

@router.delete("/sessions", summary="撤销所有其他会话")
async def revoke_all_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤销当前用户的所有其他会话（保留当前会话）"""
    # 获取当前会话的 session_id
    from app.utils.auth import decode_access_token
    auth_header = request.headers.get("Authorization")
    current_session_id = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        payload = decode_access_token(token)
        if payload:
            current_session_id = payload.get("sid")
    
    if not current_session_id:
        raise HTTPException(status_code=400, detail="无法识别当前会话")
    
    # 撤销所有其他会话
    await revoke_all_other_sessions(db, current_user.id, current_session_id)
    
    client_ip = request.client.host if request.client else "unknown"
    asyncio.create_task(add_audit_log(
        "DELETE",
        "/api/auth/sessions",
        200,
        client_ip,
        0,
        payload=f"用户 {current_user.username} 撤销所有其他会话"
    ))
    
    return {"message": "所有其他会话已撤销"}
