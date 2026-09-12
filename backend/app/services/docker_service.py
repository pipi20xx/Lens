"""兼容 shim：实现已拆分至 app/services/docker/ 包，外部引用路径保持不变。"""
from app.services.docker import DockerService

__all__ = ["DockerService"]
