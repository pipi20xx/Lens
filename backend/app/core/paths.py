"""统一的数据目录定义。

所有需要写 /app/data 下子目录的模块都应从这里取路径，
通过环境变量 DATA_DIR 可整体重定向（如本地开发）。
"""
import os

DATA_DIR = os.getenv("DATA_DIR", "/app/data")

NAV_ICONS_DIR = os.path.join(DATA_DIR, "nav_icons")
NAV_BACKGROUNDS_DIR = os.path.join(DATA_DIR, "nav_backgrounds")
WALLPAPER_DIR = os.path.join(DATA_DIR, "wallpaper")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
AUDIT_LOG_DIR = os.path.join(LOGS_DIR, "audit")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
SECRET_KEY_FILE = os.path.join(DATA_DIR, "secret_key")


def ensure_runtime_dirs():
    """启动时确保运行时目录存在"""
    for d in (DATA_DIR, NAV_ICONS_DIR, NAV_BACKGROUNDS_DIR, LOGS_DIR, AUDIT_LOG_DIR):
        os.makedirs(d, exist_ok=True)
