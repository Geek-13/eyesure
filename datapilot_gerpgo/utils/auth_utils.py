"""
认证相关工具函数
"""
import hashlib
import jwt
import time
import logging
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_token(user_id, expires_in=3600):
    """
    生成JWT令牌
    
    Args:
        user_id: 用户ID
        expires_in: 令牌有效期（秒）
        
    Returns:
        str: JWT令牌
    """
    try:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        
        return token
    except Exception as e:
        logger.error(f"生成令牌失败: {str(e)}")
        return None


def verify_token(token):
    """
    验证JWT令牌
    
    Args:
        token: JWT令牌
        
    Returns:
        dict: 令牌负载信息，如果验证失败则返回None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("令牌已过期")
        return None
    except jwt.InvalidTokenError:
        logger.warning("无效的令牌")
        return None
    except Exception as e:
        logger.error(f"验证令牌失败: {str(e)}")
        return None


def hash_password(password):
    """
    对密码进行哈希处理
    
    Args:
        password: 原始密码
        
    Returns:
        str: 哈希后的密码
    """
    try:
        # 使用SHA256哈希算法
        hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return hashed
    except Exception as e:
        logger.error(f"密码哈希处理失败: {str(e)}")
        raise


def generate_signature(params, secret_key):
    """
    生成API请求签名
    
    Args:
        params: 请求参数
        secret_key: 密钥
        
    Returns:
        str: 签名
    """
    try:
        # 对参数进行排序
        sorted_params = sorted(params.items())
        
        # 构建签名字符串
        sign_str = ''.join([f'{k}={v}' for k, v in sorted_params]) + secret_key
        
        # 计算MD5哈希
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
        
        return sign
    except Exception as e:
        logger.error(f"生成签名失败: {str(e)}")
        raise


def validate_signature(params, secret_key, signature):
    """
    验证API请求签名
    
    Args:
        params: 请求参数
        secret_key: 密钥
        signature: 待验证的签名
        
    Returns:
        bool: 签名是否有效
    """
    try:
        # 生成期望的签名
        expected_signature = generate_signature(params, secret_key)
        
        # 比较签名
        return expected_signature == signature
    except Exception as e:
        logger.error(f"验证签名失败: {str(e)}")
        return False


def get_timestamp():
    """
    获取当前时间戳（毫秒）
    
    Returns:
        str: 时间戳字符串
    """
    return str(int(time.time() * 1000))


def is_token_expired(token_data):
    """
    检查令牌是否过期
    
    Args:
        token_data: 令牌数据，包含exp字段
        
    Returns:
        bool: 是否已过期
    """
    if not token_data or 'exp' not in token_data:
        return True
    
    current_time = datetime.utcnow().timestamp()
    return current_time > token_data['exp']