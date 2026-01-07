"""
请求处理工具函数
"""
import logging
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def create_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504)):
    """
    创建配置了重试策略的requests会话
    
    Args:
        retries: 重试次数
        backoff_factor: 退避因子
        status_forcelist: 触发重试的HTTP状态码列表
        
    Returns:
        requests.Session: 配置好的会话对象
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "PUT", "POST", "PATCH", "DELETE"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def make_request(method: str, url: str, **kwargs) -> Tuple[bool, Any]:
    """
    发送HTTP请求并处理响应
    
    Args:
        method: HTTP方法（GET, POST, PUT, DELETE等）
        url: 请求URL
        **kwargs: 传递给requests的其他参数
        
    Returns:
        Tuple[bool, Any]: (是否成功, 响应数据或错误信息)
    """
    try:
        # 创建会话
        session = create_session()
        
        # 记录请求信息
        logger.debug(f"发送{method}请求到{url}")
        if 'data' in kwargs:
            logger.debug(f"请求数据: {json.dumps(kwargs['data'])}]")
        if 'params' in kwargs:
            logger.debug(f"请求参数: {kwargs['params']}")
        
        # 发送请求
        response = session.request(method, url, **kwargs)
        
        # 检查响应状态
        response.raise_for_status()
        
        # 尝试解析JSON响应
        try:
            data = response.json()
            logger.debug(f"响应数据: {json.dumps(data)}")
            return True, data
        except json.JSONDecodeError:
            # 如果不是JSON响应，返回原始文本
            text = response.text
            logger.debug(f"响应文本: {text}")
            return True, text
            
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP错误: {e}")
        logger.error(f"响应内容: {response.text if 'response' in locals() else '无响应'}")
        try:
            # 尝试获取错误响应中的JSON数据
            if 'response' in locals():
                error_data = response.json()
                return False, error_data
        except (json.JSONDecodeError, AttributeError):
            pass
        return False, {'error': str(e), 'status_code': response.status_code if 'response' in locals() else None}
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: {e}")
        return False, {'error': f'连接错误: {str(e)}'}
    
    except requests.exceptions.Timeout as e:
        logger.error(f"请求超时: {e}")
        return False, {'error': f'请求超时: {str(e)}'}
    
    except Exception as e:
        logger.error(f"请求异常: {e}")
        return False, {'error': f'请求异常: {str(e)}'}


def get_request(url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
    """
    发送GET请求
    
    Args:
        url: 请求URL
        params: 请求参数
        headers: 请求头
        **kwargs: 传递给make_request的其他参数
        
    Returns:
        Tuple[bool, Any]: (是否成功, 响应数据或错误信息)
    """
    return make_request('GET', url, params=params, headers=headers, **kwargs)


def post_request(url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, headers: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
    """
    发送POST请求
    
    Args:
        url: 请求URL
        data: 表单数据
        json_data: JSON数据
        headers: 请求头
        **kwargs: 传递给make_request的其他参数
        
    Returns:
        Tuple[bool, Any]: (是否成功, 响应数据或错误信息)
    """
    if json_data is not None:
        return make_request('POST', url, json=json_data, headers=headers, **kwargs)
    return make_request('POST', url, data=data, headers=headers, **kwargs)


def put_request(url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, headers: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
    """
    发送PUT请求
    
    Args:
        url: 请求URL
        data: 表单数据
        json_data: JSON数据
        headers: 请求头
        **kwargs: 传递给make_request的其他参数
        
    Returns:
        Tuple[bool, Any]: (是否成功, 响应数据或错误信息)
    """
    if json_data is not None:
        return make_request('PUT', url, json=json_data, headers=headers, **kwargs)
    return make_request('PUT', url, data=data, headers=headers, **kwargs)


def delete_request(url: str, headers: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
    """
    发送DELETE请求
    
    Args:
        url: 请求URL
        headers: 请求头
        **kwargs: 传递给make_request的其他参数
        
    Returns:
        Tuple[bool, Any]: (是否成功, 响应数据或错误信息)
    """
    return make_request('DELETE', url, headers=headers, **kwargs)


def join_url(base_url: str, endpoint: str) -> str:
    """
    拼接基础URL和端点
    
    Args:
        base_url: 基础URL
        endpoint: API端点
        
    Returns:
        str: 完整的URL
    """
    return urljoin(base_url, endpoint)


def format_query_params(params: Dict) -> Dict:
    """
    格式化查询参数
    
    Args:
        params: 原始参数字典
        
    Returns:
        Dict: 格式化后的参数字典
    """
    formatted_params = {}
    
    for key, value in params.items():
        # 处理None值
        if value is None:
            continue
        
        # 处理布尔值
        if isinstance(value, bool):
            formatted_params[key] = 'true' if value else 'false'
        # 处理日期时间对象
        elif hasattr(value, 'isoformat'):
            formatted_params[key] = value.isoformat()
        # 处理列表或元组
        elif isinstance(value, (list, tuple)):
            formatted_params[key] = ','.join(str(item) for item in value)
        # 其他类型直接转换为字符串
        else:
            formatted_params[key] = str(value)
    
    return formatted_params


def handle_pagination(response_data: Dict, current_page: int = 1, page_size: int = 100) -> Dict:
    """
    处理分页数据
    
    Args:
        response_data: 响应数据
        current_page: 当前页码
        page_size: 每页数量
        
    Returns:
        Dict: 包含分页信息的数据
    """
    # 提取数据
    items = response_data.get('items', [])
    total_count = response_data.get('totalCount', len(items))
    total_pages = (total_count + page_size - 1) // page_size
    
    # 构建分页信息
    pagination = {
        'current_page': current_page,
        'page_size': page_size,
        'total_count': total_count,
        'total_pages': total_pages,
        'has_next': current_page < total_pages,
        'has_prev': current_page > 1
    }
    
    return {
        'items': items,
        'pagination': pagination
    }