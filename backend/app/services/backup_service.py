import os
import time
import subprocess
import tarfile
import shutil
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.backup import BackupHistory
from app.utils.logger import logger
from app.core.config_manager import get_config, save_config
from app.services.notification_service import NotificationService
from app.services.pgsql_service import PostgresService
from app.schemas.pgsql import PostgresConfig

class BackupService:
    _scheduler = None
    _is_running = False

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
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
            logger.info(f"⏰ [Backup] 定时任务调度器已启动 (时区: {os.getenv('TZ', 'UTC')})")
            await cls.reload_tasks()

    @classmethod
    async def reload_tasks(cls):
        """从 config.json 加载并重载所有定时任务"""
        scheduler = cls.get_scheduler()
        scheduler.remove_all_jobs()
        config = get_config()
        tasks = config.get("backup_tasks", [])
        
        import os
        import pytz
        tz_name = os.getenv("TZ", "UTC")
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC
        
        for task in tasks:
            if not task.get("enabled", True):
                continue
            
            try:
                task_id = task.get("id")
                schedule_type = task.get("schedule_type") # 'cron' or 'interval'
                schedule_value = task.get("schedule_value")
                
                if schedule_type == "cron":
                    trigger = CronTrigger.from_crontab(schedule_value, timezone=tz)
                elif schedule_type == "interval":
                    # 假设 value 是分钟
                    trigger = IntervalTrigger(minutes=int(schedule_value), timezone=tz)
                else:
                    continue

                scheduler.add_job(
                    cls.run_backup_task,
                    trigger=trigger,
                    args=[task_id],
                    id=f"backup_{task_id}",
                    replace_existing=True
                )
                logger.info(f"✅ [Backup] 已挂载定时任务: {task.get('name')} ({schedule_value})")
            except Exception as e:
                logger.error(f"❌ [Backup] 加载任务 {task.get('name')} 失败: {e}")

    @classmethod
    async def run_backup_task(cls, task_id: str):
        """执行备份任务的核心入口"""
        from app.services.docker_service import DockerService
        config = get_config()
        tasks = config.get("backup_tasks", [])
        task = next((t for t in tasks if t.get("id") == task_id), None)
        
        if not task:
            logger.error(f"❌ [Backup] 找不到任务 ID: {task_id}")
            return

        host_id = task.get("host_id", "local")
        is_remote = host_id != "local"

        # 1. 初始化执行记录
        history_id = None
        try:
            async with AsyncSessionLocal() as db:
                history = BackupHistory(
                    task_id=task_id,
                    task_name=task.get("name"),
                    mode=task.get("mode"),
                    status="running"
                )
                db.add(history)
                await db.commit()
                await db.refresh(history)
                history_id = history.id
        except Exception as e:
            logger.error(f"❌ [Backup] 创建执行记录失败: {e}")

        start_time = time.time()
        logger.info(f"🚀 [Backup] 开始执行备份任务: {task.get('name')} ({'远程' if is_remote else '本地'})")
        
        success = False
        message = ""
        output_path = ""
        total_size = 0

        try:
            mode = task.get("mode", "7z")
            src = task.get("src_path")
            dst_dir = task.get("dst_path")
            os.makedirs(dst_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 提前定义 base_name，防止 UnboundLocalError
            base_name = os.path.basename(src.rstrip("/")) if src else "backup"

            if mode == "pgsql":
                # --- PostgreSQL 备份逻辑 ---
                pgsql_host_id = task.get("pgsql_host_id")
                db_names = task.get("db_names", [])
                
                if not pgsql_host_id:
                    raise Exception("未指定 PostgreSQL 主机")
                if not db_names:
                    raise Exception("未指定要备份的数据库")

                # 获取主机配置
                pgsql_hosts = config.get("pgsql_hosts", [])
                host_info = next((h for h in pgsql_hosts if h.get("id") == pgsql_host_id), None)
                if not host_info:
                    raise Exception(f"找不到 PostgreSQL 主机配置: {pgsql_host_id}")
                
                pgsql_config = PostgresConfig(**host_info)
                
                # 执行备份
                backup_files = []
                for dbname in db_names:
                    logger.info(f"📦 [Backup] 正在备份数据库: {dbname}...")
                    filename = await PostgresService.create_backup(pgsql_config, dbname)
                    # PostgresService.create_backup 默认存在 data/backups/pg
                    # 我们需要将其移动到任务指定的 dst_path
                    src_file = os.path.join("data", "backups", "pg", filename)
                    dst_file = os.path.join(dst_dir, filename)
                    shutil.move(src_file, dst_file)
                    backup_files.append(dst_file)
                
                # 如果有多个库，最后打包成一个 (可选，这里先简单记录最后一个或者全部大小)
                success = True
                message = f"已成功备份 {len(db_names)} 个数据库: {', '.join(db_names)}"
                # 对于多文件备份，我们将最后一个作为 output_path 或记录所在目录
                output_path = dst_dir
                total_size = sum(os.path.getsize(f) for f in backup_files) / (1024 * 1024)
            
            elif is_remote:
                # --- 远程备份逻辑 ---
                base_name = os.path.basename(src.rstrip("/")) if src else "remote_backup"
                hosts = config.get("docker_hosts", [])
                host_config = next((h for h in hosts if h.get("id") == host_id), None)
                if not host_config:
                    raise Exception(f"找不到远程主机配置: {host_id}")
                
                service = DockerService(host_config)
                
                # 1. 获取远程所有文件列表 (相对路径)
                logger.info(f"🔍 [Backup] 正在扫描远程文件列表...")
                find_res = service.exec_command(f"find . -type f", cwd=src)
                if not find_res["success"]:
                    raise Exception(f"无法扫描远程目录: {find_res['stderr']}")
                
                all_remote_paths = find_res["stdout"].strip().split("\n")
                all_remote_paths = [p[2:] if p.startswith("./") else p for p in all_remote_paths]

                # 2. 使用 BackupFilter 在本地进行精准过滤
                from app.utils.backup_filter import BackupFilter
                flt = BackupFilter(task.get("ignore_patterns", []))
                allowed_paths = flt.filter_paths(all_remote_paths)
                
                if not allowed_paths:
                    raise Exception("过滤后没有发现需要备份的文件")

                # 3. 将清单上传到远程
                remote_list_file = f"/tmp/lens_list_{task_id}.txt"
                list_content = "\n".join(allowed_paths)
                if not service.write_file(remote_list_file, list_content):
                    raise Exception("无法上传备份清单到远程主机")

                # 4. 根据清单进行打包
                mode = task.get("mode", "tar")
                password = task.get("password")
                
                if mode == "7z":
                    ext = ".7z"
                    remote_tmp_file = f"/tmp/lens_bk_{task_id}_{timestamp}.7z"
                    backup_cmd = f"cd {src} && 7z a {remote_tmp_file} @{remote_list_file}"
                    if password:
                        backup_cmd += f" -p{password} -mhe=on"
                else:
                    ext = ".tar.gz"
                    remote_tmp_file = f"/tmp/lens_bk_{task_id}_{timestamp}.tar.gz"
                    backup_cmd = f"tar -czf {remote_tmp_file} -C {src} -T {remote_list_file}"

                logger.info(f"📦 [Backup] 正在远程执行精准打包 ({mode})...")
                res = service.exec_command(backup_cmd)
                service.exec_command(f"rm {remote_list_file}") # 清理清单

                if not res["success"]:
                    err_msg = res["stderr"]
                    if mode == "7z" and "not found" in err_msg.lower():
                        err_msg = "远程主机未安装 7zip，请安装或改用 tar 模式。"
                    raise Exception(f"远程打包失败: {err_msg}")

                # 5. 下载到本地
                local_tmp_path = os.path.join(dst_dir, f"{base_name}_{timestamp}{ext}")
                logger.info(f"🚚 [Backup] 正在拉取远程备份文件 ({mode}) 到本地...")
                
                def download_remote():
                    import paramiko
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    try:
                        ssh.connect(host_config.get("ssh_host"), 
                                    port=host_config.get("ssh_port", 22), 
                                    username=host_config.get("ssh_user"), 
                                    password=host_config.get("ssh_pass"))
                        sftp = ssh.open_sftp()
                        sftp.get(remote_tmp_file, local_tmp_path)
                        sftp.remove(remote_tmp_file) # 清理远程临时文件
                        sftp.close()
                        return True
                    except Exception as de:
                        logger.error(f"SFTP Download Error: {de}")
                        return False
                    finally:
                        ssh.close()

                if await asyncio.to_thread(download_remote):
                    output_path = local_tmp_path
                    success = True
                    message = "远程备份完成"
                else:
                    raise Exception("从远程服务器拉取文件失败")

            else:
                # --- 原有本地备份逻辑 ---
                if not os.path.exists(src):
                    raise Exception(f"源路径不存在: {src}")
                
                if mode == "7z":
                    output_path = os.path.join(dst_dir, f"{base_name}_{timestamp}.7z")
                    success, message = await asyncio.to_thread(
                        cls._run_7z,
                        src, output_path, 
                        password=task.get("password"), 
                        ignore_patterns=task.get("ignore_patterns"),
                        level=task.get("compression_level", 1),
                        storage_type=task.get("storage_type", "ssd")
                    )
                elif mode == "tar":
                    output_path = os.path.join(dst_dir, f"{base_name}_{timestamp}.tar.gz")
                    success, message = await asyncio.to_thread(cls._run_tar, src, output_path, task.get("ignore_patterns"))
                elif mode == "sync":
                    output_path = os.path.join(dst_dir, base_name)
                    success, message = await asyncio.to_thread(
                        cls._run_sync,
                        src, output_path, 
                        ignore_patterns=task.get("ignore_patterns"),
                        storage_type=task.get("storage_type", "ssd"),
                        strategy=task.get("sync_strategy", "mirror")
                    )
            
            if success and output_path and os.path.exists(output_path) and os.path.isfile(output_path):
                total_size = os.path.getsize(output_path) / (1024 * 1024) # MB
            
        except Exception as e:
            success = False
            message = str(e)
            logger.error(f"❌ [Backup] 任务 {task.get('name')} 运行时异常: {e}")

        # 2. 更新执行记录 (确保最终状态得到更新)
        if history_id:
            try:
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(BackupHistory)
                        .where(BackupHistory.id == history_id)
                        .values(
                            status="success" if success else "failed",
                            end_time=datetime.now(),
                            size=total_size,
                            message=message[:500] if message else "", # 防止消息过长
                            output_path=output_path
                        )
                    )
                    await db.commit()
            except Exception as e:
                logger.error(f"❌ [Backup] 更新执行记录失败: {e}")
        
        duration = time.time() - start_time
        logger.info(f"🏁 [Backup] 任务 {task.get('name')} 执行完毕 (耗时: {duration:.1f}s, 状态: {'成功' if success else '失败'})")

        # 发送通知
        try:
            event = "backup.success" if success else "backup.failed"
            title = "备份成功" if success else "备份失败"
            msg = f"任务: {task.get('name')}\n模式: {task.get('mode')}\n耗时: {duration:.1f}s"
            if not success:
                msg += f"\n错误: {message}"
            else:
                msg += f"\n大小: {total_size:.2f} MB"
                
            await NotificationService.emit(event, title, msg)
        except Exception as e:
            logger.warning(f"⚠️ [Backup] 发送通知失败: {e}")

    @classmethod
    async def run_restore_task(cls, history_id: int, clear_dst: bool = False):
        """还原备份的核心入口"""
        async with AsyncSessionLocal() as db:
            # ... 获取 history 和 task 的逻辑保持不变 ...
            result = await db.execute(select(BackupHistory).where(BackupHistory.id == history_id))
            history = result.scalar_one_or_none()
            if not history:
                return False, "未找到历史记录"
            
            config = get_config()
            tasks = config.get("backup_tasks", [])
            task = next((t for t in tasks if t.get("id") == history.task_id), None)
            
            if not task:
                return False, "未找到关联的任务配置"

            src_file = history.output_path
            dst_dir = task.get("src_path")
            mode = history.mode
            password = task.get("password")

            if not os.path.exists(src_file):
                return False, f"备份文件已丢失: {src_file}"

            # 如果开启了清空还原
            if clear_dst and os.path.exists(dst_dir):
                logger.warning(f"🧹 [Backup] 正在清空目标目录: {dst_dir}")
                try:
                    for item in os.listdir(dst_dir):
                        item_path = os.path.join(dst_dir, item)
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                except Exception as e:
                    return False, f"清空目标目录失败: {str(e)}"

            logger.info(f"⏪ [Backup] 开始还原任务 ({'清空' if clear_dst else '覆盖'}): {task.get('name')}")
            
            async def do_restore():
                try:
                    if mode == "7z":
                        cmd = ["7z", "x", src_file, f"-o{dst_dir}", "-y"]
                        if password: cmd.append(f"-p{password}")
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode != 0: return False, res.stderr
                    
                    elif mode == "tar":
                        with tarfile.open(src_file, "r:gz") as tar:
                            tar.extractall(path=dst_dir)
                    
                    elif mode == "sync":
                        cmd = ["rsync", "-av", "--delete", src_file.rstrip("/") + "/", dst_dir.rstrip("/") + "/"]
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode != 0: return False, res.stderr
                    return True, "还原成功"
                except Exception as ex:
                    return False, str(ex)

            success, message = await asyncio.to_thread(lambda: asyncio.run(do_restore()) if asyncio.iscoroutinefunction(do_restore) else do_restore())
            # 简化一下，直接在 thread 跑同步逻辑
            def sync_restore():
                try:
                    if mode == "7z":
                        cmd = ["7z", "x", src_file, f"-o{dst_dir}", "-y"]
                        if password: cmd.append(f"-p{password}")
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode != 0: return False, res.stderr
                    elif mode == "tar":
                        with tarfile.open(src_file, "r:gz") as tar:
                            tar.extractall(path=dst_dir)
                    elif mode == "sync":
                        cmd = ["rsync", "-av", "--delete", src_file.rstrip("/") + "/", dst_dir.rstrip("/") + "/"]
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode != 0: return False, res.stderr
                    return True, "还原成功"
                except Exception as ex: return False, str(ex)

            success, message = await asyncio.to_thread(sync_restore)
            
            if success:
                logger.info(f"✨ [Backup] 任务 {task.get('name')} 还原成功")
            else:
                logger.error(f"❌ [Backup] 还原失败: {message}")
                
            return success, message

    @staticmethod
    def _run_7z(src, dst, password=None, ignore_patterns=None, level=1, storage_type="ssd"):
        """调用 7z 执行备份，使用预生成的清单文件"""
        from app.utils.backup_filter import BackupFilter
        
        # 1. 生成清单文件
        list_file = f"{dst}.list.txt"
        flt = BackupFilter(ignore_patterns or [])
        file_count = flt.generate_file_list(src, list_file)
        
        if file_count == 0:
            if os.path.exists(list_file): os.remove(list_file)
            return False, "没有找到符合备份条件的文件"

        # 2. 构造 7z 命令使用清单文件 (@)
        # 注意：7z a dst @list_file，我们需要在 src 的父目录下运行，这样相对路径才正确
        working_dir = os.path.dirname(src.rstrip("/"))
        
        cmd = ["7z", "a", dst, f"@{list_file}", f"-mx={level}"]
        
        if storage_type == "cloud":
            cmd.append("-mmt=on")
        elif storage_type == "hdd":
            cmd.append("-mmt=2")
        
        if password:
            cmd.append(f"-p{password}")
            cmd.append("-mhe=on")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=working_dir)
            # 清理临时清单
            if os.path.exists(list_file): os.remove(list_file)
            
            if result.returncode == 0:
                return True, f"成功备份 {file_count} 个文件"
            else:
                return False, result.stderr
        except Exception as e:
            if os.path.exists(list_file): os.remove(list_file)
            return False, str(e)

    @staticmethod
    def _run_tar(src, dst, ignore_patterns=None):
        """使用清单文件执行 tar 备份以支持过滤"""
        from app.utils.backup_filter import BackupFilter
        
        list_file = f"{dst}.list.txt"
        flt = BackupFilter(ignore_patterns or [])
        file_count = flt.generate_file_list(src, list_file)

        if file_count == 0:
            if os.path.exists(list_file): os.remove(list_file)
            return False, "没有符合条件的文件"

        working_dir = os.path.dirname(src.rstrip("/"))
        # 使用 tar -T 从清单读取文件列表
        cmd = ["tar", "-czf", dst, "-T", list_file]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=working_dir)
            if os.path.exists(list_file): os.remove(list_file)
            
            if result.returncode == 0:
                return True, f"成功打包 {file_count} 个文件"
            else:
                return False, result.stderr
        except Exception as e:
            if os.path.exists(list_file): os.remove(list_file)
            return False, str(e)

    @staticmethod
    def _run_sync(src, dst, ignore_patterns=None, storage_type="ssd", strategy="mirror"):
        """使用 rsync 执行增量同步"""
        try:
            # 基础参数：归档模式、详细输出
            cmd = ["rsync", "-av"]
            
            # 如果是镜像模式，则添加 --delete 以删除目标目录中多余的文件
            if strategy == "mirror":
                cmd.append("--delete")
            
            # 针对不同存储介质的优化
            if storage_type == "cloud":
                cmd.extend(["--no-owner", "--no-group", "--no-perms", "--size-only"])
            elif storage_type == "hdd":
                # 机械硬盘：减少随机 IO 压力
                pass
            
            cmd.extend([src.rstrip("/") + "/", dst.rstrip("/") + "/"])
            
            if ignore_patterns:
                for p in ignore_patterns:
                    cmd.append(f"--exclude={p}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True, "OK"
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_history(limit=50):
        """获取最近的备份记录"""
        # 注意：这里需要异步处理，暂时仅定义接口
        pass
