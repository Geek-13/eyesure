"""
基础API客户端类
提供与API交互的通用功能
"""
import requests
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """基础API客户端类，提供HTTP请求的封装"""
    
    def __init__(self, base_url: str, auth_type: str = 'api_key', timeout: int = 30):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL
            auth_type: 认证类型，默认为'api_key'
            timeout: 请求超时时间，默认为30秒
        """
        self.base_url = base_url.rstrip('/')
        self.auth_type = auth_type
        self.timeout = timeout
        self.session = requests.Session()
        self.auth_token = None
        self.token_expiry = None
        
    def set_auth_token(self, token: str, expiry: Optional[float] = None) -> None:
        """设置认证令牌"""
        self.auth_token = token
        self.token_expiry = expiry
        
    def is_token_valid(self) -> bool:
        """检查令牌是否有效"""
        if not self.auth_token:
            return False
        if self.token_expiry and time.time() > self.token_expiry:
            return False
        return True
    
    def refresh_token(self) -> bool:
        """刷新认证令牌，子类需要实现"""
        raise NotImplementedError("子类必须实现refresh_token方法")
    
    def _prepare_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """准备请求参数"""
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        # 准备headers
        headers = kwargs.pop('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        
        # 添加认证信息
        if self.is_token_valid():
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        # 处理请求数据
        if 'data' in kwargs and isinstance(kwargs['data'], dict):
            kwargs['data'] = json.dumps(kwargs['data'])
        
        return {
            'method': method,
            'url': url,
            'headers': headers,
            'timeout': self.timeout,
            **kwargs
        }
    
    def _handle_response(self, response: requests.Response) -> Tuple[bool, Any]:
        """处理API响应"""
        try:
            response.raise_for_status()
            try:
                return True, response.json()
            except json.JSONDecodeError:
                return True, response.text
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP错误: {e}")
            logger.error(f"响应内容: {response.text}")
            try:
                return False, response.json()
            except json.JSONDecodeError:
                return False, {'error': str(e), 'status_code': response.status_code}
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return False, {'error': str(e)}
    
    def request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, Any]:
        """发送HTTP请求"""
        # 确保令牌有效
        if not self.is_token_valid() and self.auth_type == 'oauth2':
            if not self.refresh_token():
                return False, {'error': '认证令牌无效且无法刷新'}
        
        # 准备请求
        request_kwargs = self._prepare_request(method, endpoint, **kwargs)
        
        # 发送请求
        logger.debug(f"发送请求: {request_kwargs['method']} {request_kwargs['url']}")
        try:
            response = self.session.request(**request_kwargs)
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            return False, {'error': f'请求异常: {str(e)}'}
    
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
        """发送GET请求"""
        return self.request('GET', endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
        """发送POST请求"""
        return self.request('POST', endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Tuple[bool, Any]:
        """发送PUT请求"""
        return self.request('PUT', endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Tuple[bool, Any]:
        """发送DELETE请求"""
        return self.request('DELETE', endpoint, **kwargs)