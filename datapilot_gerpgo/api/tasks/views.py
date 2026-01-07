from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import logging
import json
from datetime import datetime
from datetime import datetime

from .models import ScheduledTask, TaskExecutionLog
from .serializers import ScheduledTaskSerializer, TaskExecutionLogSerializer
from .schedule_tasks import (
    add_or_update_task,
    remove_task,
    pause_task,
    resume_task,
    get_scheduler_status,
    execute_task_now
)

logger = logging.getLogger(__name__)


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """定时任务视图集"""
    queryset = ScheduledTask.objects.all().order_by('-created_at')
    serializer_class = ScheduledTaskSerializer
    
    def dispatch(self, request, *args, **kwargs):
        # 高级请求调试
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"\n{'='*80}")
        print(f"[DEBUG] [{timestamp}] 开始请求处理 - {request.method} {request.path}")
        print(f"[DEBUG] 请求头:")
        for key, value in request.headers.items():
            print(f"[DEBUG]   {key}: {value}")
        
        # 读取原始请求体
        raw_body = request.body.decode('utf-8') if request.body else ""
        print(f"[DEBUG] 原始请求体长度: {len(raw_body)} 字节")
        print(f"[DEBUG] 原始请求体: {raw_body}")
        
        # 检查Content-Type
        content_type = request.content_type or "未指定"
        print(f"[DEBUG] Content-Type: {content_type}")
        
        # 检查是否有调试头
        debug_headers = {k: v for k, v in request.headers.items() if k.startswith('X-Debug-')}
        if debug_headers:
            print(f"[DEBUG] 调试头:")
            for key, value in debug_headers.items():
                print(f"[DEBUG]   {key}: {value}")
        
        # 尝试解析JSON
        if content_type == 'application/json' and raw_body:
            try:
                parsed_body = json.loads(raw_body)
                print(f"[DEBUG] 解析后的请求体类型: {type(parsed_body).__name__}")
                print(f"[DEBUG] 解析后的请求体键: {list(parsed_body.keys()) if isinstance(parsed_body, dict) else '不是字典'}")
                print(f"[DEBUG] 解析后的请求体: {parsed_body}")
                
                # 检查是否存在错误的字段名
                incorrect_fields = []
                if 'function_path' in parsed_body:
                    incorrect_fields.append('function_path')
                if 'enabled' in parsed_body:
                    incorrect_fields.append('enabled')
                if 'description' in parsed_body:
                    incorrect_fields.append('description')
                if 'params' in parsed_body and 'params_dict' not in parsed_body:
                    incorrect_fields.append('params')
                
                if incorrect_fields:
                    print(f"[DEBUG] 警告: 请求中包含错误字段名: {', '.join(incorrect_fields)}")
                    print(f"[DEBUG] 期望的字段名: task_function, status, params_dict")
                else:
                    print(f"[DEBUG] 请求字段名看起来正确")
                    
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON解析错误: {e}")
        
        # 继续处理请求
        try:
            response = super().dispatch(request, *args, **kwargs)
            print(f"[DEBUG] [{timestamp}] 请求处理完成 - 状态码: {response.status_code}")
            print(f"{'='*80}\n")
            return response
        except Exception as e:
            print(f"[DEBUG] [{timestamp}] 请求处理异常: {str(e)}")
            print(f"{'='*80}\n")
            raise
    
    def perform_create(self, serializer):
        """创建任务时的处理"""
        # 添加调试日志
        print(f"[DEBUG] 接收到创建任务请求，数据: {self.request.data}")
        
        try:
            # 验证序列化器数据
            print(f"[DEBUG] 序列化器验证前数据: {serializer.initial_data}")
            if serializer.is_valid():
                print(f"[DEBUG] 序列化器验证通过，有效数据: {serializer.validated_data}")
                task = serializer.save()
                print(f"[DEBUG] 任务保存成功，ID: {task.id}")
                try:
                    # 如果任务是激活状态，添加到调度器
                    print(f"[DEBUG] 检查任务状态: {task.status}")
                    if task.status == 'ACTIVE':
                        print(f"[DEBUG] 将任务添加到调度器")
                        add_or_update_task(task)
                except Exception as e:
                    # 如果添加到调度器失败，回滚任务状态
                    task.status = 'INACTIVE'
                    task.save(update_fields=['status'])
                    print(f"[DEBUG] 添加到调度器失败，状态已回滚: {str(e)}")
                    logger.error(f"创建任务后添加到调度器失败: {str(e)}")
                    raise
            else:
                print(f"[DEBUG] 序列化器验证失败，错误: {serializer.errors}")
                raise Exception(f"序列化器验证失败: {serializer.errors}")
        except Exception as e:
            print(f"[DEBUG] 创建任务时发生错误: {str(e)}")
            raise
    
    def perform_update(self, serializer):
        """更新任务时的处理"""
        # 添加调试日志
        print(f"[DEBUG] 接收到更新任务请求，任务ID: {self.kwargs.get('pk')}")
        print(f"[DEBUG] 更新数据: {self.request.data}")
        
        try:
            # 验证序列化器数据
            print(f"[DEBUG] 序列化器验证前数据: {serializer.initial_data}")
            if serializer.is_valid():
                print(f"[DEBUG] 序列化器验证通过，有效数据: {serializer.validated_data}")
                old_task = self.get_object()
                old_status = old_task.status
                print(f"[DEBUG] 原始任务状态: {old_status}")
                
                task = serializer.save()
                print(f"[DEBUG] 任务更新成功，ID: {task.id}")
                
                try:
                    # 更新调度器中的任务
                    print(f"[DEBUG] 更新调度器中的任务")
                    add_or_update_task(task)
                    
                    # 如果任务状态从激活变为非激活，需要从调度器移除
                    if old_status == 'ACTIVE' and task.status != 'ACTIVE':
                        print(f"[DEBUG] 任务状态从激活变为非激活，从调度器移除")
                        remove_task(task.id)
                except Exception as e:
                    print(f"[DEBUG] 更新调度器失败: {str(e)}")
                    logger.error(f"更新任务后更新调度器失败: {str(e)}")
                    raise
            else:
                print(f"[DEBUG] 序列化器验证失败，错误: {serializer.errors}")
                raise Exception(f"序列化器验证失败: {serializer.errors}")
        except Exception as e:
            print(f"[DEBUG] 更新任务时发生错误: {str(e)}")
            raise
    
    def perform_destroy(self, instance):
        """删除任务时的处理"""
        task_id = instance.id
        instance.delete()
        
        # 从调度器移除任务
        remove_task(task_id)
    
    @action(detail=True, methods=['post'], url_path='execute-now')
    def execute_now(self, request, pk=None):
        """立即执行任务"""
        try:
            task = self.get_object()
            success = execute_task_now(task.id)
            
            if success:
                return Response({
                    'message': f'任务 "{task.name}" 已触发执行，请稍后查看执行结果',
                    'task_id': task.id
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': '触发任务执行失败'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"执行任务失败: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='pause')
    def pause(self, request, pk=None):
        """暂停任务"""
        try:
            task = self.get_object()
            if pause_task(task.id):
                # 更新任务状态
                task.status = 'PAUSED'
                task.save(update_fields=['status'])
                return Response({
                    'message': f'任务 "{task.name}" 已暂停'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': '暂停任务失败'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"暂停任务失败: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='resume')
    def resume(self, request, pk=None):
        """恢复任务"""
        try:
            task = self.get_object()
            task.status = 'ACTIVE'
            task.save(update_fields=['status'])
            
            # 添加到调度器
            add_or_update_task(task)
            
            return Response({
                'message': f'任务 "{task.name}" 已恢复'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # 恢复失败，回滚状态
            task.status = 'PAUSED'
            task.save(update_fields=['status'])
            logger.error(f"恢复任务失败: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='status')
    @method_decorator(cache_page(5))  # 缓存5秒
    def scheduler_status(self, request):
        """获取调度器状态"""
        status_info = get_scheduler_status()
        return Response(status_info)
    
    @action(detail=False, methods=['get'], url_path='task-list-options')
    def task_list_options(self, request):
        """获取可用的任务函数列表"""
        # 使用正确的函数路径格式，基于实际的函数位置
        task_options = [
            {
                'value': 'api.views.sync_products_from_gerpgo',
                'label': '同步产品数据'
            },
            {
                'value': 'api.views.sync_fba_inventory_from_gerpgo',
                'label': '同步FBA库存数据'
            },
            {
                'value': 'api.views.sync_marketplaces_from_gerpgo',
                'label': '同步店铺市场数据'
            },
            {
                'value': 'api.views.sync_sp_ad_data_from_gerpgo',
                'label': '同步SP广告产品数据'
            },
            {
                'value': 'api.views.sync_sp_kw_data_from_gerpgo',
                'label': '同步SP广告关键词数据'
            },
            {
                'value': 'api.views.sync_sp_target_data_from_gerpgo',
                'label': '同步SP广告投放数据'
            },
            {
                'value': 'api.views.sync_sp_placement_data_from_gerpgo',
                'label': '同步SP广告展示位置数据'
            },
            {
                'value': 'api.views.sync_sp_search_terms_data_from_gerpgo',
                'label': '同步SP广告搜索词数据'
            },
            {
                'value': 'api.views.sync_sb_kw_data_from_gerpgo',
                'label': '同步SB广告关键词数据'
            },
            {
                'value': 'api.views.sync_sb_campaign_data_from_gerpgo',
                'label': '同步SB广告活动数据'
            },
            {
                'value': 'api.views.sync_sb_creative_data_from_gerpgo',
                'label': '同步SB广告创意数据'
            },
            {
                'value': 'api.views.sync_sb_targeting_data_from_gerpgo',
                'label': '同步SB广告投放数据'
            },
            {
                'value': 'api.views.sync_sb_placement_data_from_gerpgo',
                'label': '同步SB广告展示位置数据'
            },
            {
                'value': 'api.views.sync_sb_search_terms_data_from_gerpgo',
                'label': '同步SB广告搜索词数据'
            },
            {
                'value': 'api.views.sync_sd_campaign_data_from_gerpgo',
                'label': '同步SD广告活动数据'
            },
            {
                'value': 'api.views.sync_sd_product_data_from_gerpgo',
                'label': '同步SD广告产品数据'
            },
            {
                'value': 'api.views.sync_inventory_storage_ledger_from_gerpgo',
                'label': '同步库存分类账数据'
            },
            {
                'value': 'api.views.sync_inventory_storage_ledger_detail',
                'label': '同步库存分类账详情数据'
            },
            {
                'value': 'api.views.sync_transaction',
                'label': '同步交易数据'
            },
            {
                'value': 'api.views.sync_traffic_analysis',
                'label': '同步流量分析数据'
            },
            {
                'value': 'api.views.sync_fba_inventory_full_from_gerpgo',
                'label': '同步restock数据'
            },
            {
                'value': 'api.views.sync_mon_storage_fee',
                'label': '同步库存仓储费'
            },
            {
                'value': 'api.views.sync_profit_analysis',
                'label': '同步利润分析数据'
            },
            {
                'value': 'api.views.sync_currency_rates',
                'label': '同步汇率数据'
            },
        ]
        return Response(task_options)


class TaskExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """任务执行日志视图集"""
    queryset = TaskExecutionLog.objects.all().order_by('-started_at')
    serializer_class = TaskExecutionLogSerializer
    
    def get_queryset(self):
        """支持按任务筛选"""
        queryset = super().get_queryset()
        task_id = self.request.query_params.get('task_id')
        
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='recent')
    def recent_logs(self, request):
        """获取最近的执行日志"""
        # 获取最近100条日志
        recent_logs = self.get_queryset()[:100]
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='statistics')
    def execution_statistics(self, request):
        """获取执行统计信息"""
        total = TaskExecutionLog.objects.count()
        success_count = TaskExecutionLog.objects.filter(status='SUCCESS').count()
        failure_count = TaskExecutionLog.objects.filter(status='FAILURE').count()
        running_count = TaskExecutionLog.objects.filter(status='RUNNING').count()
        
        # 计算成功率
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        stats = {
            'total_executions': total,
            'success_count': success_count,
            'failure_count': failure_count,
            'running_count': running_count,
            'success_rate': round(success_rate, 2)
        }
        
        return Response(stats)