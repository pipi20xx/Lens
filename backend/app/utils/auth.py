from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt
import bcrypt
import os
import secrets
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.services.config_service import ConfigService
from app.utils.logger import logger

def _load_secret_key() -> str:
    """密钥来源优先级：环境变量 > data/secret_key 持久化文件 > 自动生成并持久化。

    不再回退到硬编码密钥，避免可预测密钥被用于伪造 token。
    """
    env_key = os.getenv("JWT_SECRET_KEY")
    if env_key:
        return env_key

    from app.core.paths import SECRET_KEY_FILE
    key_file = SECRET_KEY_FILE
    try:
        with open(key_file, "r", encoding="utf-8") as f:
            stored = f.read().strip()
            if stored:
                return stored
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning(f"⚠️ [Auth] 读取密钥文件失败: {e}")

    generated = secrets.token_hex(32)
    try:
        os.makedirs(os.path.dirname(key_file) or ".", exist_ok=True)
        with open(key_file, "w", encoding="utf-8") as f:
            f.write(generated)
        os.chmod(key_file, 0o600)
        logger.info(f"🔐 [Auth] 已生成新的 JWT 密钥并保存到 {key_file}")
    except OSError as e:
        # 只读文件系统等场景：退回每次重启随机的密钥（所有用户需重新登录）
        logger.warning(f"⚠️ [Auth] 无法持久化 JWT 密钥（{e}），本次运行使用临时密钥，重启后所有登录将失效")
    return generated

SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 默认登录有效期 24 小时

def verify_password(plain_password: str, hashed_password: str):
    """校验明文密码与哈希值是否匹配"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str):
    """对明文密码进行加密"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT 访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """解析并验证 JWT 令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """获取当前用户的核心依赖项 (支持 JWT 和 静态 API Token)"""
    
    auth_header = request.headers.get("Authorization")
    token = auth_header.replace("Bearer ", "") if auth_header and auth_header.startswith("Bearer ") else None
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # A. 尝试作为 JWT 令牌解析
        payload = decode_access_token(token)
        if payload and payload.get("type") != "2fa_pending":
            username = payload.get("sub")
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalars().first()
            if user:
                return user
        
        # B. 尝试作为 静态 API Token 匹配
        static_token = await ConfigService.get("api_token")
        if static_token and token == static_token:
            result = await db.execute(select(User).where(User.username == "admin"))
            return result.scalars().first()
    except HTTPException:
        raise
    except Exception:
        pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )