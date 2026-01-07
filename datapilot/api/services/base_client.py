import os
import json
import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BaseAPIClient:
    """API客户端基础类"""
    def __init__(self, base_url, auth_type='bearer', timeout=30):
        self.base_url = base_url
        self.auth_type = auth_type
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        self.auth_token = None
        self.token_expires_at = None
    
    def set_auth_token(self, token, expires_in=None):
        """设置认证令牌"""
        self.auth_token = token
        if expires_in:
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 提前60秒刷新
        self.headers[f'Authorization'] = f'{self.auth_type} {token}'
    
    def is_token_valid(self):
        """检查令牌是否有效"""
        if not self.auth_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at
    
    def refresh_token(self):
        """刷新令牌，子类需要实现"""
        raise NotImplementedError("子类必须实现refresh_token方法")
    
    def _prepare_request(self):
        """准备请求，确保令牌有效"""
        if not self.is_token_valid():
            self.refresh_token()
    
    def get(self, endpoint, params=None):
        """发送GET请求"""
        self._prepare_request()
        url = f'{self.base_url}{endpoint}'
        try:
            response = self.session.get(url, headers=self.headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GET请求失败: {url}, 错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}, 响应内容: {e.response.text}")
            raise
    
    def post(self, endpoint, data=None):
        """发送POST请求"""
        self._prepare_request()
        url = f'{self.base_url}{endpoint}'
        try:
            response = self.session.post(url, headers=self.headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"POST请求失败: {url}, 数据: {data}, 错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}, 响应内容: {e.response.text}")
            raise
    
    def put(self, endpoint, data=None):
        """发送PUT请求"""
        self._prepare_request()
        url = f'{self.base_url}{endpoint}'
        try:
            response = self.session.put(url, headers=self.headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"PUT请求失败: {url}, 数据: {data}, 错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}, 响应内容: {e.response.text}")
            raise
    
    def delete(self, endpoint):
        """发送DELETE请求"""
        self._prepare_request()
        url = f'{self.base_url}{endpoint}'
        try:
            response = self.session.delete(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            # DELETE请求通常没有响应体
            if response.text:
                return response.json()
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE请求失败: {url}, 错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}, 响应内容: {e.response.text}")
            raise