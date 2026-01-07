from django.apps import AppConfig
from django.core.management import execute_from_command_line
import logging
import atexit
import threading
import os

logger = logging.getLogger(__name__)

# 全局标志，防止调度器被重复启动
_scheduler_started = False
_scheduler_lock = threading.Lock()


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    
    def ready(self):
        """应用启动时初始化调度器"""
        global _scheduler_started
        
        # 避免在Django管理命令执行时重复启动调度器
        import sys
        if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'dumpdata', 'loaddata', 'shell']):
            return
        
        # 防止Django自动重载器导致的重复启动
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        # 只在Django应用正式启动时启动调度器，不限制具体命令
        with _scheduler_lock:
            # 使用全局标志确保调度器只启动一次
            if not _scheduler_started:
                try:
                    # 延迟导入，避免循环依赖
                    from .tasks import start_scheduler
                    
                    # 启动调度器
                    start_scheduler()
                    _scheduler_started = True
                    logger.info("调度器已在应用启动时初始化")
                    
                    # 注册退出处理函数，在应用关闭时停止调度器
                    atexit.register(self.cleanup)
                except Exception as e:
                    logger.error(f"启动调度器失败: {str(e)}")
                    # 重置标志，允许下次尝试
                    _scheduler_started = False
            else:
                logger.debug("调度器已经启动过，跳过重复启动")
    
    def cleanup(self):
        """应用关闭时清理资源"""
        try:
            # 延迟导入，避免循环依赖
            from .tasks import stop_scheduler
            
            stop_scheduler()
            logger.info("调度器已在应用关闭时停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {str(e)}")
