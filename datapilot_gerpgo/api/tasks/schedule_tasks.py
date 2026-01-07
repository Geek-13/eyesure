from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from django.apps import apps
from django.conf import settings
import importlib
import logging
from datetime import datetime
import threading
import traceback

from .models import ScheduledTask, TaskExecutionLog

logger = logging.getLogger(__name__) # 初始化                                                             任务调度器日志记录器

# 创建线程池执行器
executors = {
    'default': ThreadPoolExecutor(10)  # 最多10个并发线程
}

# 创建调度器实例，调度器作用是定时执行任务
scheduler = BackgroundScheduler(executors=executors, timezone=settings.TIME_ZONE)

# 存储任务ID映射：{scheduled_task_id: job_id}
task_job_map = {}

# 线程锁，用于保护task_job_map，确保在多线程环境下安全操作
job_map_lock = threading.Lock()

# 全局标志，防止任务被重复加载
_tasks_loaded = False
_load_lock = threading.Lock()


def import_function(function_path):
    """根据函数路径导入函数"""
    try:
        # 添加详细日志记录
        logger.info(f"尝试导入函数: {function_path}")
        
        # 验证函数路径格式
        if '.' not in function_path:
            raise ValueError(f"函数路径格式错误，缺少模块名: {function_path}")
        
        # 分割模块路径和函数名
        module_path, function_name = function_path.rsplit('.', 1)
        logger.info(f"分割后的模块路径: {module_path}, 函数名: {function_name}")
        
        # 尝试导入模块
        logger.info(f"正在导入模块: {module_path}")
        module = importlib.import_module(module_path)
        
        # 尝试获取函数
        logger.info(f"正在获取函数: {function_name}")
        function = getattr(module, function_name)
        
        # 验证是否为可调用对象
        if not callable(function):
            raise TypeError(f"{function_path} 不是可调用的函数")
        
        logger.info(f"成功导入函数: {function_path}")
        return function
    except (ImportError, AttributeError, ValueError) as e:
        # 详细的错误日志，包括推荐的格式
        error_info = f"导入函数失败: {function_path}, 错误: {str(e)}"
        logger.error(error_info)
        logger.error(f"提示: 函数路径应使用正确格式，例如: 'api.views.sync_products_from_gerpgo'")
        
        # 增强错误信息，提供更明确的指导
        if isinstance(e, ImportError):
            error_info += f"\n请检查模块路径是否正确，当前尝试导入: {module_path}"
        elif isinstance(e, AttributeError):
            error_info += f"\n请检查函数名是否正确，当前尝试获取: {function_name}"
        
        raise ImportError(error_info)


def task_wrapper(task_id):
    """任务包装器，用于捕获异常并记录执行日志"""
    from django.http import HttpRequest
    from datetime import timezone
    
    task = ScheduledTask.objects.get(id=task_id)
    # 使用带时区的datetime
    now = datetime.now(timezone.utc)
    execution_log = TaskExecutionLog.objects.create(task=task, started_at=now)
    
    try:
        logger.info(f"开始执行任务: {task.name} (ID: {task.id})")
        
        # 导入并执行任务函数
        func = import_function(task.task_function)
        params = task.get_params_dict()
        
        # 执行任务函数
        # 检查是否为Django视图函数（需要request参数）
        result = None
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        logger.info(f"执行函数: {func_name}")
        
        # 检查是否为Django视图类（可能需要.as_view()）
        if hasattr(func, 'as_view') and callable(getattr(func, 'as_view')):
            logger.info(f"检测到Django视图类，调用as_view()方法")
            # 对于视图类，使用as_view()方法获取可调用对象
            view_func = func.as_view()
            # 创建模拟的request对象
            request = HttpRequest()
            # 默认为POST请求
            request.method = 'POST'
            # 设置request.data，包含任务参数
            request.data = params.copy()
            # 执行视图函数，不需要额外传递kwargs
            result = view_func(request)
        else:
            # 尝试直接执行
            try:
                # 尝试直接执行（非视图函数）
                result = func(**params)
            except TypeError as e:
                # 如果缺少request参数，可能是Django视图函数
                if 'missing 1 required positional argument: \'request\'' in str(e):
                    logger.info("检测到可能是Django视图函数，创建模拟request对象")
                    # 创建模拟的request对象
                    request = HttpRequest()
                    # 设置基本属性
                    request.method = 'POST'
                    request.POST = {}
                    request.GET = {}
                    request.META = {
                        'CONTENT_TYPE': 'application/json',
                        'HTTP_USER_AGENT': 'Scheduler/1.0',
                        'REMOTE_ADDR': '127.0.0.1',
                    }
                    request.headers = {}
                    request.path = '/api/scheduler/task'
                    request.path_info = request.path
                    # 为可能的lower()调用设置默认值
                    if not hasattr(request, 'content_type'):
                        request.content_type = 'application/json'
                    
                    # 对于Django REST framework视图，需要设置request.data
                    # 我们将任务参数设置到request.data中
                    request.data = params.copy()
                    
                    # 不需要将params作为kwargs传递，因为我们已经将其设置到request对象中
                    result = func(request)
                else:
                    # 其他类型错误则重新抛出
                    raise
        
        # 更新任务状态，确保使用带时区的datetime
        now = datetime.now(timezone.utc)
        execution_log.status = 'SUCCESS'
        execution_log.message = f"任务执行成功: {str(result) if result is not None else '无返回值'}"
        execution_log.finished_at = now
        # 计算执行时间时确保两个时间都有时区信息
        execution_log.execution_time = (now - execution_log.started_at).total_seconds()
        execution_log.save()
        
        # 更新任务的最后执行时间
        task.last_executed = now
        task.save(update_fields=['last_executed'])
        
        logger.info(f"任务执行成功: {task.name} (ID: {task.id})")
        
    except Exception as e:
        # 记录错误信息，确保使用带时区的datetime
        now = datetime.now(timezone.utc)
        error_message = f"任务执行失败: {str(e)}\n{traceback.format_exc()}"
        execution_log.status = 'FAILURE'
        execution_log.message = error_message
        execution_log.finished_at = now
        # 计算执行时间时确保两个时间都有时区信息
        execution_log.execution_time = (now - execution_log.started_at).total_seconds()
        execution_log.save()
        
        logger.error(f"任务执行失败: {task.name} (ID: {task.id}), 错误: {str(e)}")
        logger.error(traceback.format_exc())


def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        scheduler.start()
        logger.info("调度器已启动")
        # 加载所有激活的任务
        load_all_active_tasks()
    else:
        logger.warning("调度器已经在运行")


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown()
        with job_map_lock:
            task_job_map.clear()
        logger.info("调度器已停止")
    else:
        logger.warning("调度器未运行")



def load_all_active_tasks():
    """加载所有激活的任务"""
    global _tasks_loaded
    
    with _load_lock:
        active_tasks = ScheduledTask.objects.filter(status='ACTIVE')
        
        # 清除现有的任务映射，准备重新加载
        with job_map_lock:
            # 先移除所有调度器中的任务
            for job_id in task_job_map.values():
                try:
                    scheduler.remove_job(job_id)
                except Exception as e:
                    logger.warning(f"移除旧任务失败: {job_id}, 错误: {str(e)}")
            # 清空任务映射
            task_job_map.clear()
        
        # 重新加载所有激活的任务
        for task in active_tasks:
            add_or_update_task(task)
        
        _tasks_loaded = True
        logger.info(f"已加载 {len(active_tasks)} 个激活的定时任务")


def add_or_update_task(task):
    """添加或更新任务"""
    with job_map_lock:
        # 如果任务处于激活状态，则添加到调度器
        if task.status == 'ACTIVE':
            try:
                # 验证函数是否存在
                import_function(task.task_function)
                
                # 解析cron表达式
                cron_parts = task.cron_expression.split()
                if len(cron_parts) != 5:
                    raise ValueError(f"无效的cron表达式: {task.cron_expression}")
                
                minute, hour, day, month, day_of_week = cron_parts
                
                # 创建触发器
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )
                
                # 检查任务是否已经存在于调度器中
                if task.id in task_job_map:
                    # 任务已存在，先移除旧任务
                    logger.debug(f"任务已存在，先移除旧任务: {task.name} (ID: {task.id})")
                    try:
                        scheduler.remove_job(task_job_map[task.id])
                    except Exception as e:
                        logger.warning(f"移除旧任务失败: {task.name} (ID: {task.id}), 错误: {str(e)}")
                
                # 添加或更新任务到调度器
                job_id = scheduler.add_job(
                    func=task_wrapper,
                    trigger=trigger,
                    args=[task.id],
                    id=f"task_{task.id}",
                    name=task.name,
                    replace_existing=True
                ).id
                
                # 更新映射
                task_job_map[task.id] = job_id
                logger.info(f"已添加/更新任务: {task.name} (ID: {task.id}), Cron: {task.cron_expression}")
                
            except Exception as e:
                logger.error(f"添加/更新任务失败: {task.name} (ID: {task.id}), 错误: {str(e)}")
                raise
        else:
            # 如果任务不是激活状态，移除调度器中的任务
            if task.id in task_job_map:
                logger.debug(f"任务不是激活状态，移除调度器中的任务: {task.name} (ID: {task.id})")
                try:
                    scheduler.remove_job(task_job_map[task.id])
                    del task_job_map[task.id]
                    logger.info(f"已移除非激活任务: {task.name} (ID: {task.id})")
                except Exception as e:
                    logger.warning(f"移除任务失败: {task.name} (ID: {task.id}), 错误: {str(e)}")
                    # 即使移除失败，也要更新映射
                    del task_job_map[task.id]


def remove_task(task_id):
    """移除任务"""
    with job_map_lock:
        if task_id in task_job_map:
            try:
                scheduler.remove_job(task_job_map[task_id])
                del task_job_map[task_id]
                logger.info(f"已移除任务 (ID: {task_id})")
                return True
            except Exception as e:
                logger.error(f"移除任务失败 (ID: {task_id}), 错误: {str(e)}")
                return False
        return False


def pause_task(task_id):
    """暂停任务"""
    with job_map_lock:
        if task_id in task_job_map:
            try:
                scheduler.pause_job(task_job_map[task_id])
                logger.info(f"已暂停任务 (ID: {task_id})")
                return True
            except Exception as e:
                logger.error(f"暂停任务失败 (ID: {task_id}), 错误: {str(e)}")
                return False
        return False


def resume_task(task_id):
    """恢复任务"""
    with job_map_lock:
        if task_id in task_job_map:
            try:
                scheduler.resume_job(task_job_map[task_id])
                logger.info(f"已恢复任务 (ID: {task_id})")
                return True
            except Exception as e:
                logger.error(f"恢复任务失败 (ID: {task_id}), 错误: {str(e)}")
                return False
        return False


def get_scheduler_status():
    """获取调度器状态"""
    return {
        'running': scheduler.running,
        'job_count': len(scheduler.get_jobs()),
        'mapped_tasks': list(task_job_map.keys())
    }


def execute_task_now(task_id):
    """立即执行指定任务"""
    try:
        task = ScheduledTask.objects.get(id=task_id)
        # 在新线程中执行任务
        thread = threading.Thread(target=task_wrapper, args=[task_id])
        thread.daemon = True
        thread.start()
        logger.info(f"已触发立即执行任务: {task.name} (ID: {task_id})")
        return True
    except Exception as e:
        logger.error(f"触发立即执行任务失败 (ID: {task_id}), 错误: {str(e)}")
        return False