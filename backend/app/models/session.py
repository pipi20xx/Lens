from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.session import Base
from datetime import datetime

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_id = Column(String(64), unique=True, index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    device_info = Column(String(100))
    browser_info = Column(String(100))
    login_time = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Integer, default=1)
