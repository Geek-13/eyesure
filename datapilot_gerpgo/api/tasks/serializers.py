from rest_framework import serializers
from .models import ScheduledTask, TaskExecutionLog
import json


class ScheduledTaskSerializer(serializers.ModelSerializer):
    """定时任务序列化器"""
    # 将后端的params字段转换为前端可用的params_dict
    params_dict = serializers.JSONField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = ScheduledTask
        fields = ['id', 'name', 'task_function', 'cron_expression', 'params', 'params_dict', 
                 'status', 'created_at', 'updated_at', 'last_executed']
        read_only_fields = ['created_at', 'updated_at', 'last_executed']
    
    def validate_cron_expression(self, value):
        """验证cron表达式格式"""
        # 简单验证：检查是否包含5个部分
        parts = value.strip().split()
        if len(parts) != 5:
            raise serializers.ValidationError('Cron表达式格式错误，需要5个部分：分 时 日 月 周')
        return value
    
    def validate_params(self, value):
        """验证params字段是否为有效的JSON字符串"""
        if value:
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError('参数必须是有效的JSON格式')
        return value
    
    def validate_params_dict(self, value):
        # 调试日志
        print(f"[DEBUG] 验证params_dict值: {value} (类型: {type(value).__name__})")
        
        # 验证params_dict是否为有效的JSON对象
        if value is not None and not isinstance(value, dict):
            error_msg = f"params_dict必须是一个有效的JSON对象，当前类型: {type(value).__name__}"
            print(f"[DEBUG] params_dict验证失败: {error_msg}")
            raise serializers.ValidationError(error_msg)
        return value
    
    def create(self, validated_data):
        print(f"[DEBUG] Serializer create方法 - 验证后数据: {validated_data}")
        
        # 处理params_dict参数
        params_dict = validated_data.pop('params_dict', {})
        print(f"[DEBUG] 提取的params_dict: {params_dict}")
        
        # 确保params_dict是字典类型
        if params_dict is None:
            params_dict = {}
        elif not isinstance(params_dict, dict):
            params_dict = {}
            print(f"[DEBUG] params_dict不是字典类型，已转换为空字典")
        
        # 将params_dict转换为JSON字符串并存入params字段
        try:
            validated_data['params'] = json.dumps(params_dict, ensure_ascii=False)
            print(f"[DEBUG] 转换后的params字符串: {validated_data['params']}")
        except Exception as e:
            print(f"[DEBUG] JSON序列化失败: {str(e)}")
            validated_data['params'] = '{}'
        
        print(f"[DEBUG] 最终保存的数据: {validated_data}")
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        print(f"[DEBUG] Serializer update方法 - 验证后数据: {validated_data}")
        print(f"[DEBUG] 更新前实例数据: {instance.__dict__}")
        
        # 处理params_dict参数
        if 'params_dict' in validated_data:
            params_dict = validated_data.pop('params_dict', {})
            print(f"[DEBUG] 提取的params_dict: {params_dict}")
            
            # 确保params_dict是字典类型
            if params_dict is None:
                params_dict = {}
            elif not isinstance(params_dict, dict):
                params_dict = {}
                print(f"[DEBUG] params_dict不是字典类型，已转换为空字典")
            
            # 将params_dict转换为JSON字符串并存入params字段
            try:
                validated_data['params'] = json.dumps(params_dict, ensure_ascii=False)
                print(f"[DEBUG] 转换后的params字符串: {validated_data['params']}")
            except Exception as e:
                print(f"[DEBUG] JSON序列化失败: {str(e)}")
                validated_data['params'] = '{}'
        
        print(f"[DEBUG] 最终更新的数据: {validated_data}")
        return super().update(instance, validated_data)
    
    def to_internal_value(self, data):
        print(f"[DEBUG] Serializer接收到的原始数据: {data}")
        result = super().to_internal_value(data)
        print(f"[DEBUG] 内部转换后的数据: {result}")
        return result


class TaskExecutionLogSerializer(serializers.ModelSerializer):
    """任务执行日志序列化器"""
    task_name = serializers.CharField(source='task.name', read_only=True)
    task_function = serializers.CharField(source='task.task_function', read_only=True)
    
    class Meta:
        model = TaskExecutionLog
        fields = ['id', 'task', 'task_name', 'task_function', 'status', 'message', 
                 'started_at', 'finished_at', 'execution_time']
        read_only_fields = ['task', 'status', 'message', 'started_at', 'finished_at', 'execution_time']