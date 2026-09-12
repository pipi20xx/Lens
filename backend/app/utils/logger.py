import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import List, Dict, Any
import asyncio

# 日志根目录
from app.core.paths import LOGS_DIR as LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

class LogFormatter(logging.Formatter):
    """带颜色的控制台格式化"""
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: "%(asctime)s | 🔍 %(message)s",
        logging.INFO: blue + "%(asctime)s | %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s | ⚠️ %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s | ❌ %(message)s" + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(asctime)s | %(message)s")
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

# 实时广播管理器
class LogBroadcaster:
    def __init__(self):
        self.subscribers = set()

    def subscribe(self):
        queue = asyncio.Queue()
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.subscribers.discard(queue)

    async def broadcast(self, message):
        for queue in list(self.subscribers):
            try:
                await queue.put(message)
            except Exception:
                pass

log_broadcaster = LogBroadcaster()

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(log_broadcaster.broadcast(msg))
        except Exception:
            pass

class DailyFileHandler(logging.FileHandler):
    """自定义处理程序：始终以 YYYY-MM-DD.log 命名，并在跨天时自动切换"""
    def __init__(self, dirname, backupCount=7, encoding='utf-8'):
        self.dirname = dirname
        self.backupCount = backupCount
        self.encoding = encoding
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.dirname, f"{self.current_date}.log")
        super().__init__(log_file, encoding=encoding)

    def emit(self, record):
        # 每次写入前检查日期
        new_date = datetime.now().strftime("%Y-%m-%d")
        if new_date != self.current_date:
            self.current_date = new_date
            # 关闭旧文件，开启新文件
            self.stream.close()
            self.baseFilename = os.path.join(self.dirname, f"{self.current_date}.log")
            self.stream = self._open()
            # 简单的清理逻辑：保留最近 backupCount 天的日志
            self._cleanup_old_logs()
        super().emit(record)

    def _cleanup_old_logs(self):
        try:
            files = [f for f in os.listdir(self.dirname) if f.endswith(".log")]
            files.sort(reverse=True)
            if len(files) > self.backupCount:
                for old_file in files[self.backupCount:]:
                    os.remove(os.path.join(self.dirname, old_file))
        except Exception:
            pass

def setup_logger():
    logger = logging.getLogger("Lens")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    # 1. 控制台
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(LogFormatter())
    
    # 2. WebSocket 队列
    q_handler = QueueHandler()
    q_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S"))
    
    # 3. 自定义动态日期文件处理器 (方案 B)
    file_handler = DailyFileHandler(LOG_DIR, backupCount=7, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    
    logger.addHandler(stdout_handler)
    logger.addHandler(q_handler)
    logger.addHandler(file_handler)
    
    logger.propagate = False
    return logger
    
    # 禁用日志向上传播，防止重复记录到 uvicorn 的 root logger
    logger.propagate = False
    
    return logger

logger = setup_logger()

# 辅助函数：模拟审计风格日志
# 是否输出性能审计行（⏱️ [性能审计]），跟随「启用审计日志」开关（audit_enabled）。
# audit_log 会被服务代码同步调用，这里用模块级开关变量，由 main.py 启动和配置更新接口写入。
perf_audit_enabled = True

def set_perf_audit_enabled(enabled: bool):
    global perf_audit_enabled
    perf_audit_enabled = bool(enabled)

def audit_log(title: str, duration_ms: float, details: List[str]):
    if not perf_audit_enabled:
        return
    # 性能审计深度降噪：过滤掉耗时低于 300ms 的所有常规请求
    # 300ms 以内的响应在内网环境下属于正常波动，不具备审计价值
    if duration_ms < 300:
        return

    detail_str = " | ".join(details)
    logger.info(f"⏱️ [性能审计]: {title} 耗时 {duration_ms:.0f}ms | {detail_str}")

# 系统日志 API 相关逻辑
def get_log_dates() -> List[str]:
    """获取所有存在日志的日期列表"""
    files = [f.replace(".log", "") for f in os.listdir(LOG_DIR) if f.endswith(".log")]
    return sorted(files, reverse=True)

def get_log_content(date: str) -> str:
    """读取指定日期的完整日志文本"""
    path = os.path.join(LOG_DIR, f"{date}.log")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Log file not found."

def get_last_n_logs(n: int = 100) -> List[str]:
    """获取当前日志文件最后的 n 行，用于 WebSocket 初始化回填"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(LOG_DIR, f"{current_date}.log")
    if not os.path.exists(path):
        return []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            # 简单实现：读取最后 n 行
            lines = f.readlines()
            return [line.strip() for line in lines[-n:]]
    except Exception:
        return []
