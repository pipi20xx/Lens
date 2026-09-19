"""Docker 自动更新：定时任务调度器。"""
import asyncio

from app.utils.logger import logger

from .base import DockerServiceBase


class AutoUpdateMixin(DockerServiceBase):
    _scheduler = None
    _is_running = False

    @staticmethod
    async def run_auto_update_task():
        """
        极致精准版：根据记录中的 host_id 直接定点更新
        """
        logger.info("🚀 [Docker] 开始执行每日自动更新任务...")
        from app.core.config_manager import get_config
        from app.services.notification_service import NotificationService
        
        config = get_config()
        # 检查是否全局开启了自动更新
        auto_settings = config.get("docker_auto_update_settings", {"enabled": True})
        if not auto_settings.get("enabled"):
            logger.info("ℹ️ [Docker] 自动更新已全局关闭，跳过执行。")
            return

        all_hosts = config.get("docker_hosts", [])
        container_settings = config.get("docker_container_settings", {})
        
        # 1. 筛选出所有开启了自动更新且有 host_id 的记录
        tasks_by_host = {}
        for name, settings in container_settings.items():
            if settings.get("auto_update") and settings.get("host_id"):
                h_id = settings.get("host_id")
                if h_id not in tasks_by_host:
                    tasks_by_host[h_id] = []
                tasks_by_host[h_id].append(name)
        
        if not tasks_by_host:
            logger.info("ℹ️ [Docker] 没有发现待更新的任务记录，任务结束。")
            return

        updated_count = 0
        error_count = 0

        # 2. 定点执行
        for h_id, names in tasks_by_host.items():
            host_config = next((h for h in all_hosts if h.get("id") == h_id), None)
            if not host_config:
                logger.error(f"❌ [Docker] 找不到 ID 为 {h_id} 的主机配置，跳过容器: {names}")
                continue

            host_name = host_config.get("name", "Unknown")
            logger.info(f"🌐 [Docker] 正在连接主机 [{host_name}] 检查容器: {', '.join(names)}")
            
            try:
                from app.services.docker_service import DockerService
                service = DockerService(host_config)
                # 使用 to_thread 异步获取容器列表
                containers = await asyncio.to_thread(service.list_containers, True, {"name": names})
                
                for container in containers:
                    c_name = container.get("name")
                    if c_name in names:
                        image = container.get("image")
                        try:
                            update_info = await service.get_image_update_info(image)
                            if update_info and update_info.get("has_update"):
                                logger.info(f"✨ [Docker][{host_name}] 发现镜像更新: {c_name}")
                                c_id = container.get("full_id") or container.get("id")
                                # 使用 to_thread 异步执行重构操作
                                if await asyncio.to_thread(service.container_action, c_id, "recreate"):
                                    updated_count += 1
                                    await NotificationService.emit(
                                        event="docker.auto_update",
                                        title="Docker 自动更新成功",
                                        message=f"主机: {host_name}\n容器: {c_name}\n镜像: {image}\n结果: 已更新并重构"
                                    )
                                else:
                                    error_count += 1
                        except Exception as e:
                            logger.error(f"❌ [Docker][{host_name}] 处理 {c_name} 异常: {e}")
                            error_count += 1
            except Exception as e:
                logger.error(f"❌ [Docker] 无法连接主机 {host_name}: {e}")
                error_count += len(names)

        logger.info(f"🏁 [Docker] 自动更新完毕。更新: {updated_count}, 失败: {error_count}")

        if error_count > 0:
            await NotificationService.emit(
                event="docker.auto_update",
                title="Docker 自动更新存在失败",
                message=(
                    "本次自动更新已结束，但部分容器未能完成更新。\n"
                    f"成功: {updated_count} 个\n失败: {error_count} 个\n"
                    "请前往 Lens 的 Docker 管理页查看日志定位原因。"
                ),
            )

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            import os
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
            logger.info("📅 [Docker] 自动更新调度器已启动")
            await cls.reload_scheduler()

    @classmethod
    async def reload_scheduler(cls):
        """重载调度器设置"""
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        from app.core.config_manager import get_config
        import os
        import pytz
        
        scheduler = cls.get_scheduler()
        scheduler.remove_all_jobs()
        
        config = get_config()
        settings = config.get("docker_auto_update_settings", {"enabled": True, "type": "cron", "value": "03:00"})
        
        if not settings.get("enabled"):
            logger.info("📅 [Docker] 自动更新已停用")
            return

        tz_name = os.getenv("TZ", "UTC")
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        try:
            stype = settings.get("type", "cron")
            sval = settings.get("value", "03:00")
            
            if stype == "cron":
                if ":" in sval:
                    h, m = sval.split(":")
                    trigger = CronTrigger(hour=int(h), minute=int(m), timezone=tz)
                else:
                    trigger = CronTrigger.from_crontab(sval, timezone=tz)
            else: # interval (minutes)
                trigger = IntervalTrigger(minutes=int(sval), timezone=tz)

            scheduler.add_job(
                cls.run_auto_update_task,
                trigger,
                id="docker_auto_update",
                replace_existing=True
            )
            logger.info(f"📅 [Docker] 自动更新已重载 ({stype}: {sval}, 时区: {tz_name})")
        except Exception as e:
            logger.error(f"❌ [Docker] 重载调度器失败: {e}")
