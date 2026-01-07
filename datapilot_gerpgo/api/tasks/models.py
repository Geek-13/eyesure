from django.db import models
import json
from datetime import datetime


class ScheduledTask(models.Model):
    """定时任务模型"""
    # 任务名称
    name = models.CharField(max_length=200, verbose_name='任务名称')
    
    # 任务函数路径（如：api.views.sync_products_from_gerpgo）
    task_function = models.CharField(max_length=255, verbose_name='任务函数路径')
    
    # 执行频率（cron表达式）
    cron_expression = models.CharField(max_length=100, verbose_name='Cron表达式', 
                                       help_text='格式: 分 时 日 月 周')
    
    # 任务参数（JSON格式存储）
    params = models.TextField(verbose_name='任务参数', blank=True, default='{}',
                             help_text='JSON格式的参数')
    
    # 任务状态
    STATUS_CHOICES = (
        ('ACTIVE', '激活'),
        ('INACTIVE', '未激活'),
        ('PAUSED', '暂停'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                             default='INACTIVE', verbose_name='任务状态')
    
    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间') # 任务创建时间，auto_now_add=True，创建时自动设置为当前时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间') # 任务更新时间，auto_now=True，每次保存时自动更新为当前时间
    
    # 最后执行时间
    last_executed = models.DateTimeField(null=True, blank=True, verbose_name='最后执行时间')
    
    def get_params_dict(self):
        """将JSON字符串参数转换为字典"""
        try:
            return json.loads(self.params)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_params_dict(self, params_dict):
        """将字典参数转换为JSON字符串"""
        self.params = json.dumps(params_dict, ensure_ascii=False)
    
    def __str__(self):
        return f"{self.name} ({self.task_function})"
    
    class Meta:
        verbose_name = '定时任务'
        verbose_name_plural = '定时任务'
        ordering = ['-created_at']


class TaskExecutionLog(models.Model):
    """任务执行日志模型"""
    # 关联的定时任务
    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, 
                           related_name='execution_logs', verbose_name='关联任务')
    """
    task：关联的定时任务
    ScheduledTask：定时任务模型
    on_delete=models.CASCADE：级联删除，当关联的定时任务被删除时，该任务的执行日志也会被删除
    related_name='execution_logs'：关联任务的执行日志列表，用于反向查询
    """
    
    # 执行状态
    STATUS_CHOICES = (
        ('SUCCESS', '成功'),
        ('FAILURE', '失败'),
        ('RUNNING', '运行中'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, 
                             default='RUNNING', verbose_name='执行状态')
    
    # 执行结果消息
    message = models.TextField(blank=True, verbose_name='执行结果消息')
    
    # 执行开始和结束时间
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    
    # 执行时长（秒）
    execution_time = models.FloatField(null=True, blank=True, verbose_name='执行时长(秒)')
    
    def save(self, *args, **kwargs):
        """保存时计算执行时长"""
        if self.status in ['SUCCESS', 'FAILURE'] and self.finished_at and self.started_at:
            self.execution_time = (self.finished_at - self.started_at).total_seconds() # total_seconds：获取时间差的秒数
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.task.name} - {self.status} - {self.started_at}"
    

    class Meta:
        verbose_name = '任务执行日志'
        verbose_name_plural = '任务执行日志'
        ordering = ['-started_at']