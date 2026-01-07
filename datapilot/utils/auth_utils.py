"""认证工具模块

该模块提供与API认证相关的功能，包括获取和刷新访问令牌、验证令牌有效性等。
"""
import os
import time
import hashlib
import hmac
import base64
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# 缓存访问令牌，避免频繁请求
token_cache = {
    'access_token': None,
    'expires_at': 0,
}

def get_access_token(force_refresh=False):
    """获取访问令牌，如果缓存中有有效的令牌则直接返回，否则刷新令牌"""
    global token_cache
    
    # 检查缓存的令牌是否有效
    if not force_refresh and token_cache['access_token'] and token_cache['expires_at'] > time.time() + 60:
        logger.debug("使用缓存的访问令牌")
        return token_cache['access_token']
    
    # 刷新令牌
    logger.debug("刷新访问令牌")
    token_data = refresh_access_token()
    token_cache['access_token'] = token_data.get('access_token')
    token_cache['expires_at'] = time.time() + token_data.get('expires_in', 3600)
    
    return token_cache['access_token']

def refresh_access_token():
    """刷新访问令牌
    
    该函数应该根据实际的认证服务实现，这里提供一个基于settings中的配置的示例实现
    """
    from api.services.api_service1 import AmazonAdvertisingAPIService
    
    try:
        # 使用已有的API服务类来刷新令牌
        api_service = AmazonAdvertisingAPIService()
        # 刷新令牌会在API服务初始化时自动完成
        # 这里我们只需要获取当前的令牌信息
        return {
            'access_token': api_service.auth_token,
            'expires_in': 3600,  # 默认1小时有效期
        }
    except Exception as e:
        logger.error(f"刷新访问令牌失败: {str(e)}")
        raise

def validate_token(token):
    """验证令牌是否有效
    
    注意：这是一个本地验证方法，实际应用中可能需要调用认证服务进行验证
    """
    global token_cache
    
    # 检查令牌是否与缓存中的匹配且未过期
    if token == token_cache['access_token'] and token_cache['expires_at'] > time.time():
        return True
    
    # 尝试从settings中获取验证密钥进行验证（如果有）
    validation_key = getattr(settings, 'TOKEN_VALIDATION_KEY', None)
    if validation_key and token:
        # 这里是一个简单的示例验证逻辑
        # 实际应用中应该根据具体的令牌格式和验证方法实现
        try:
            # 假设令牌格式为：数据.签名
            parts = token.split('.')
            if len(parts) == 2:
                # 验证签名
                data, signature = parts
                expected_signature = generate_api_signature(data, validation_key)
                return signature == expected_signature
        except Exception as e:
            logger.error(f"令牌验证失败: {str(e)}")
    
    return False

def generate_api_signature(data, secret_key):
    """生成API签名
    
    参数:
        data: 要签名的数据
        secret_key: 签名密钥
    
    返回:
        生成的签名字符串
    """
    try:
        # 将数据和密钥转换为字节
        data_bytes = str(data).encode('utf-8')
        secret_bytes = str(secret_key).encode('utf-8')
        
        # 使用HMAC-SHA256生成签名
        signature = hmac.new(secret_bytes, data_bytes, hashlib.sha256).digest()
        
        # 将签名转换为base64编码的字符串
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        logger.error(f"生成API签名失败: {str(e)}")
        raise

def clear_token_cache():
    """清除令牌缓存"""
    global token_cache
    token_cache = {
        'access_token': None,
        'expires_at': 0,
    }
    logger.debug("令牌缓存已清除")

def get_auth_headers():
    """获取包含认证信息的请求头
    
    返回:
        包含Authorization头的字典
    """
    token = get_access_token()
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }