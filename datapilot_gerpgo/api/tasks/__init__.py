"""定时任务模块，用于管理和执行数据同步任务"""

# 模块版本信息
__version__ = '1.0.0'
__author__ = 'EYESURE'
__description__ = '定时任务管理模块，支持动态配置和执行数据同步任务'

# 注意：为了避免循环导入问题，这里不直接导入模型和视图等，而是在需要时动态导入
# 当需要使用模块中的功能时，建议直接从具体的子模块导入

# 示例使用方式：
# from api.tasks.schedule_tasks import start_scheduler, stop_scheduler
# from api.tasks.models import ScheduledTask, TaskExecutionLog
# from api.tasks.views import ScheduledTaskViewSet, TaskExecutionLogViewSet

# 仅导入不会导致循环依赖的核心功能
def start_scheduler():
    """启动调度器（包装函数，避免循环导入）"""
    from .schedule_tasks import start_scheduler as _start_scheduler
    return _start_scheduler()

def stop_scheduler():
    """停止调度器（包装函数，避免循环导入）"""
    from .schedule_tasks import stop_scheduler as _stop_scheduler
    return _stop_scheduler()