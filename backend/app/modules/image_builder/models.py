from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class BuildTaskLog(Base):
    __tablename__ = "build_task_logs"
    id = Column(String, primary_key=True, index=True) # task_id
    project_id = Column(String, index=True, nullable=False)
    tag = Column(String, nullable=False)
    status = Column(String, default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # 构建上下文信息（便于历史记录直观展示）
    image_name = Column(String, nullable=True)     # 完整镜像地址，如 registry.example.com/myimage:latest
    platforms = Column(String, nullable=True)       # 构建平台，如 linux/amd64,linux/arm64
    host_name = Column(String, nullable=True)       # 构建主机名称
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 构建完成时间