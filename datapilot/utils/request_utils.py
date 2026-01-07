"""请求工具模块

该模块提供HTTP请求相关的辅助功能，包括发送请求、处理错误、重试机制等。
"""
import time
import requests
import logging
from functools import wraps
from django.conf import settings

logger = logging.getLogger(__name__)

def make_request(url, method='GET', headers=None, params=None, data=None, json_data=None, timeout=30, verify=True):
    """发送HTTP请求
    
    参数:
        url: 请求URL
        method: 请求方法 ('GET', 'POST', 'PUT', 'DELETE'等)
        headers: 请求头
        params: URL参数
        data: 请求体数据（表单格式）
        json_data: 请求体数据（JSON格式）
        timeout: 请求超时时间（秒）
        verify: 是否验证SSL证书
    
    返回:
        请求响应对象
    
    异常:
        requests.exceptions.RequestException: 请求异常
    """
    try:
        # 准备请求参数
        request_kwargs = {
            'url': url,
            'headers': headers or {},
            'params': params,
            'timeout': timeout,
            'verify': verify,
        }
        
        # 添加请求体数据
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            if json_data is not None:
                request_kwargs['json'] = json_data
            elif data is not None:
                request_kwargs['data'] = data
        
        # 记录请求信息
        logger.debug(f"发送{method}请求到 {url}")
        if params:
            logger.debug(f"请求参数: {params}")
        if data or json_data:
            logger.debug(f"请求体数据: {data or json_data}")
        
        # 发送请求
        response = requests.request(method, **request_kwargs)
        
        # 检查响应状态码
        response.raise_for_status()
        
        # 记录响应信息
        logger.debug(f"请求成功，状态码: {response.status_code}")
        
        return response
    except requests.exceptions.RequestException as e:
        # 处理请求异常
        handle_api_error(e)
        raise

def handle_api_error(error):
    """处理API错误
    
    参数:
        error: 请求异常对象
    """
    if hasattr(error, 'response') and error.response is not None:
        # 有响应的错误
        status_code = error.response.status_code
        error_message = f"API请求失败，状态码: {status_code}"
        
        # 尝试获取错误响应内容
        try:
            error_data = error.response.json()
            error_message += f", 错误信息: {error_data}"
        except ValueError:
            # 无法解析JSON响应
            error_message += f", 响应内容: {error.response.text}"
        
        # 根据状态码提供更具体的错误信息
        if status_code == 400:
            error_message += " (错误请求: 请检查请求参数)"
        elif status_code == 401:
            error_message += " (未授权: 请检查认证信息)"
        elif status_code == 403:
            error_message += " (禁止访问: 无权限访问请求的资源)"
        elif status_code == 404:
            error_message += " (未找到: 请求的资源不存在)"
        elif status_code == 429:
            error_message += " (请求过多: 超过API速率限制)"
        elif status_code >= 500:
            error_message += " (服务器错误: 请稍后再试)"
        
        logger.error(error_message)
    else:
        # 无响应的错误（如连接超时）
        error_message = f"API请求失败: {str(error)}"
        logger.error(error_message)

def retry_on_failure(max_retries=3, delay=2, backoff=2, exceptions=(requests.exceptions.RequestException,)):
    """请求失败自动重试装饰器
    
    参数:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间乘数
        exceptions: 触发重试的异常类型
    
    返回:
        装饰后的函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    # 尝试执行函数
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    
                    # 如果是最后一次重试，则直接抛出异常
                    if retries >= max_retries:
                        logger.error(f"达到最大重试次数 ({max_retries})，请求失败")
                        raise
                    
                    # 记录重试信息
                    logger.warning(f"请求失败，将在{current_delay}秒后进行第{retries}次重试: {str(e)}")
                    
                    # 等待指定时间后重试
                    time.sleep(current_delay)
                    
                    # 增加下次重试的延迟时间
                    current_delay *= backoff
            
            # 这一行理论上不会执行到，因为最后一次重试失败会直接抛出异常
            return func(*args, **kwargs)
        return wrapper
    return decorator

def validate_response(response, expected_structure=None):
    """验证API响应数据
    
    参数:
        response: 响应对象
        expected_structure: 期望的响应结构（字典形式）
    
    返回:
        验证后的响应数据
    
    异常:
        ValueError: 响应验证失败
    """
    try:
        # 尝试解析JSON响应
        try:
            data = response.json()
        except ValueError:
            logger.error("响应不是有效的JSON格式")
            raise ValueError("响应不是有效的JSON格式")
        
        # 如果没有指定期望的结构，直接返回数据
        if expected_structure is None:
            return data
        
        # 验证响应结构
        _validate_structure(data, expected_structure)
        
        logger.debug("响应验证成功")
        return data
    except Exception as e:
        logger.error(f"响应验证失败: {str(e)}")
        raise

def _validate_structure(data, expected_structure):
    """递归验证数据结构
    
    参数:
        data: 要验证的数据
        expected_structure: 期望的数据结构
    
    异常:
        ValueError: 数据结构验证失败
    """
    # 如果期望结构是类型，检查数据是否为该类型的实例
    if isinstance(expected_structure, type):
        if not isinstance(data, expected_structure):
            raise ValueError(f"期望类型 {expected_structure.__name__}，实际类型 {type(data).__name__}")
        return
    
    # 如果期望结构是字典，检查数据是否包含所有必需的键，并且值的类型正确
    if isinstance(expected_structure, dict):
        if not isinstance(data, dict):
            raise ValueError(f"期望字典类型，实际类型 {type(data).__name__}")
        
        # 检查必需的键
        for key, expected_type in expected_structure.items():
            if key not in data:
                raise ValueError(f"缺少必需的键: {key}")
            
            # 递归验证值的结构
            _validate_structure(data[key], expected_type)
        
        return
    
    # 如果期望结构是列表，检查数据是否为列表，并且列表中的每个元素都符合期望的结构
    if isinstance(expected_structure, list):
        if not isinstance(data, list):
            raise ValueError(f"期望列表类型，实际类型 {type(data).__name__}")
        
        # 如果列表不为空，验证第一个元素的结构
        if expected_structure and data:
            expected_item_type = expected_structure[0]
            for item in data:
                _validate_structure(item, expected_item_type)
        
        return

def get_rate_limits(response):
    """从响应头中获取API速率限制信息
    
    参数:
        response: 响应对象
    
    返回:
        包含速率限制信息的字典
    """
    rate_limits = {
        'limit': None,
        'remaining': None,
        'reset': None,
    }
    
    if response and response.headers:
        # 检查常见的速率限制响应头
        limit_headers = {
            'limit': ['X-RateLimit-Limit', 'RateLimit-Limit'],
            'remaining': ['X-RateLimit-Remaining', 'RateLimit-Remaining'],
            'reset': ['X-RateLimit-Reset', 'RateLimit-Reset'],
        }
        
        for key, headers in limit_headers.items():
            for header in headers:
                if header in response.headers:
                    try:
                        # 尝试将值转换为适当的类型
                        if key == 'reset':
                            # 重置时间通常是时间戳
                            rate_limits[key] = int(response.headers[header])
                        else:
                            # 限制和剩余数量通常是整数
                            rate_limits[key] = int(response.headers[header])
                        break
                    except ValueError:
                        # 如果转换失败，保留原始字符串值
                        rate_limits[key] = response.headers[header]
    
    return rate_limits