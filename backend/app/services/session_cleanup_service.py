import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.services.session_service import cleanup_expired_sessions
from app.utils.logger import logger

class SessionCleanupService:
    _scheduler = None
    _is_running = False

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
            import pytz
            tz_name = os.getenv("TZ", "UTC")
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC
            cls._scheduler = AsyncIOScheduler(timezone=tz)
        return cls._scheduler

    @classmethod
    async def start_scheduler(cls):
        if not cls._is_running:
            cls.get_scheduler().start()
            cls._is_running = True
            logger.info(f"⏰ [Session] 定时清理任务调度器已启动 (时区: {os.getenv('TZ', 'UTC')})")
            await cls.reload_tasks()

    @classmethod
    async def reload_tasks(cls):
        """加载并重载会话清理定时任务"""
        scheduler = cls.get_scheduler()
        scheduler.remove_all_jobs()
        
        # 每小时清理一次过期会话
        scheduler.add_job(
            cls.cleanup_expired_sessions_job,
            trigger=IntervalTrigger(hours=1),
            id="cleanup_expired_sessions",
            replace_existing=True
        )
        logger.info("✅ [Session] 已挂载定时任务: 清理过期会话 (每小时执行)")

    @classmethod
    async def cleanup_expired_sessions_job(cls):
        """清理过期会话的任务"""
        try:
            async with AsyncSessionLocal() as db:
                await cleanup_expired_sessions(db)
                logger.info("🧹 [Session] 已清理过期会话")
        except Exception as e:
            logger.error(f"❌ [Session] 清理过期会话失败: {e}")
