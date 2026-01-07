import os
import logging
from .base_client import BaseAPIClient
from django.conf import settings

logger = logging.getLogger(__name__)

class AmazonAdvertisingAPIService(BaseAPIClient):
    """亚马逊广告API服务类"""
    # 区域对应的API端点
    REGION_ENDPOINTS = {
        'na': 'https://advertising-api.amazon.com',
        'eu': 'https://advertising-api-eu.amazon.com',
        'fe': 'https://advertising-api-fe.amazon.com',
    }
    
    def __init__(self):
        # 从设置中获取配置
        config = settings.AMAZON_AD_CONFIG
        region = config.get('REGION', 'na')
        base_url = self.REGION_ENDPOINTS.get(region, self.REGION_ENDPOINTS['na'])
        
        super().__init__(base_url=base_url)
        
        # 保存配置信息 - 将实例变量名改为_refresh_token以避免冲突
        self.client_id = config.get('CLIENT_ID')
        self.client_secret = config.get('CLIENT_SECRET')
        self._refresh_token = config.get('REFRESH_TOKEN')
        self.api_version = config.get('API_VERSION', 'v3')
        
        # 初始化时尝试获取令牌
        self.refresh_token()
    
    def refresh_token(self):
        """刷新访问令牌"""
        logger.info("正在刷新亚马逊广告API访问令牌")
        
        token_url = f'{self.base_url}/auth/o2/token'
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self._refresh_token,  # 更新引用
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            # 使用session发送请求，但不使用BaseClient的_prepare_request方法，避免递归调用
            response = self.session.post(token_url, data=payload, timeout=self.timeout)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)  # 默认1小时
            
            self.set_auth_token(access_token, expires_in)
            logger.info("亚马逊广告API访问令牌刷新成功")
        except Exception as e:
            logger.error(f"刷新亚马逊广告API访问令牌失败: {str(e)}")
            raise
    
    def get_profiles(self):
        """获取广告配置文件列表"""
        endpoint = f'/{self.api_version}/profiles'
        return self.get(endpoint)
    
    def get_campaigns(self, profile_id, params=None):
        """获取广告活动列表"""
        endpoint = f'/{self.api_version}/campaigns'
        # 添加配置文件ID到请求头
        headers = self.headers.copy()
        headers['Amazon-Advertising-API-Scope'] = str(profile_id)
        
        # 使用session直接发送请求，避免再次调用_prepare_request
        url = f'{self.base_url}{endpoint}'
        response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_ad_groups(self, profile_id, params=None):
        """获取广告组列表"""
        endpoint = f'/{self.api_version}/adGroups'
        headers = self.headers.copy()
        headers['Amazon-Advertising-API-Scope'] = str(profile_id)
        
        url = f'{self.base_url}{endpoint}'
        response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_keywords(self, profile_id, params=None):
        """获取关键词列表"""
        endpoint = f'/{self.api_version}/keywords'
        headers = self.headers.copy()
        headers['Amazon-Advertising-API-Scope'] = str(profile_id)
        
        url = f'{self.base_url}{endpoint}'
        response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_report(self, profile_id, report_id):
        """获取报表数据"""
        endpoint = f'/{self.api_version}/reports/{report_id}'
        headers = self.headers.copy()
        headers['Amazon-Advertising-API-Scope'] = str(profile_id)
        
        url = f'{self.base_url}{endpoint}'
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def create_report(self, profile_id, report_config):
        """创建报表"""
        endpoint = f'/{self.api_version}/reports'
        headers = self.headers.copy()
        headers['Amazon-Advertising-API-Scope'] = str(profile_id)
        
        url = f'{self.base_url}{endpoint}'
        response = self.session.post(url, headers=headers, json=report_config, timeout=self.timeout)
        response.raise_for_status()
        return response.json()