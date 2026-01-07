"""
Gerpgo API客户端
提供与Gerpgo系统交互的特定功能
"""
import hashlib
import time
import logging
import json
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import requests
from .base_client import BaseAPIClient
import datetime


logger = logging.getLogger(__name__)


class GerpgoAPIClient(BaseAPIClient):
    """Gerpgo API客户端类"""
    # 初始化客户端
    def __init__(self, appId=None, appKey=None, api_key=None, api_secret=None, 
                 base_url=None, timeout=60, max_retries=3, retry_interval=5):
        # 支持两种参数名称格式
        self.appId = appId or api_key
        self.appKey = appKey or api_secret
        self.base_url = base_url
        self.timeout = timeout  # 增加超时时间到60秒
        self.max_retries = max_retries
        self.retry_interval = retry_interval  # 增加初始重试间隔到5秒
        self.access_token = None
        self.token_expire_time = 0
        self.logger = logging.getLogger(__name__)
        
        # 调用父类初始化方法
        super().__init__(base_url=self.base_url, timeout=self.timeout)
    

    # 获取访问令牌
    def _get_access_token(self):
        """获取访问令牌"""
        try:
            logger.info("开始获取accessToken...")
            # 直接构建完整的token URL，避免urljoin拼接问题
            token_url = f"{self.base_url.rstrip('/')}/api_token"
            logger.debug(f"构建的token URL: {token_url}")
            
            # 创建会话发送请求
            session = requests.Session()
            response = session.post(
                token_url,
                json={'appId': self.appId, 'appKey': self.appKey},
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            logger.debug(f"发送请求: POST {token_url}")
            logger.debug(f"请求响应状态码: {response.status_code}")
            logger.debug(f"请求响应内容: {response.text}")
            
            # 直接处理响应
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # 检查是否为标准返回结构
                    if isinstance(data, dict) and 'code' in data:
                        # 验证状态码和数据结构
                        if data['code'] == 200 and 'data' in data and isinstance(data['data'], dict):
                            # 提取accessToken字符串
                            if 'accessToken' in data['data'] and isinstance(data['data']['accessToken'], str):
                                self.access_token = data['data']['accessToken']
                                logger.info("成功获取accessToken")
                                logger.debug(f"accessToken长度: {len(self.access_token) if self.access_token else 0}")
                                # 设置过期时间
                                if 'expiresIn' in data['data'] and isinstance(data['data']['expiresIn'], (int, float)):
                                    self.token_expire_time = int(time.time()) + int(data['data']['expiresIn']) - 300
                                    logger.debug(f"token过期时间设置为: {self.token_expire_time}")
                                else:
                                    self.token_expire_time = int(time.time()) + 3000  # 默认50分钟
                                    logger.debug("使用默认token过期时间: 50分钟")
                                return self.access_token
                            else:
                                logger.error(f"响应中缺少有效的accessToken字段: {data}")
                        else:
                            logger.error(f"响应结构不正确或状态码非200: {data}")
                    else:
                        logger.error(f"无效的JSON响应: {data}")
                except json.JSONDecodeError:
                    logger.error(f"响应不是有效的JSON格式: {response.text}")
            else:
                logger.error(f"获取accessToken失败，状态码: {response.status_code}, 响应: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"请求异常: {str(e)}")
        except Exception as e:
            logger.error(f"获取accessToken时发生未知错误: {str(e)}")
            
        # 如获取失败，重置token和过期时间
        logger.error("accessToken获取失败，重置token信息")
        self.access_token = None
        self.token_expire_time = 0
        return None
    

    # 准备请求参数
    def _prepare_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """准备请求参数，添加Gerpgo特定的认证信息"""
        # 获取基础请求参数
        request_kwargs = super()._prepare_request(method, endpoint, **kwargs)
        
        # 对于获取token的请求，不需要添加accessToken
        if endpoint == 'api_token':
            return request_kwargs
        
        # 检查token是否有效，如果无效则获取新的token
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug(f"需要获取或刷新accessToken: 当前token={'存在' if self.access_token else '不存在'}, 过期时间={self.token_expire_time}, 当前时间={current_time}")
            self.access_token = self._get_access_token()
            
        # 添加accessToken请求头
        headers = request_kwargs.get('headers', {})
        if self.access_token and isinstance(self.access_token, str):  # 添加类型检查
            headers.update({
                'accessToken': self.access_token  # 确保是字符串类型
            })
            logger.debug("已添加accessToken到请求头")
        else:
            logger.error("无法获取有效的accessToken字符串，请求可能失败")
        
        request_kwargs['headers'] = headers
        return request_kwargs
    

    # 刷新令牌
    def refresh_token(self) -> bool:
        """刷新令牌"""
        logger.info("刷新accessToken...")
        token = self._get_access_token()
        result = bool(token)
        logger.info(f"令牌刷新{'成功' if result else '失败'}")
        return result
    

    # 获取产品信息
    def get_products(self, page: int = 1, page_size: int = 100, **params) -> Tuple[bool, Any]:
        """获取产品列表"""
        logger.info(f"获取产品列表: 页码={page}, 每页数量={page_size}")
        params.update({'page': page, 'pagesize': page_size})
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取产品列表前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求产品数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，避免拼接问题
        products_url = f"{self.base_url.rstrip('/')}/operation/sale/selling/page"
        logger.debug(f"构建的产品列表URL: {products_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到产品请求头")
        
        try:
            # 修改请求方式为POST，参数放在请求体中
            response = session.post(
                products_url,
                json=params,
                headers=headers,
                timeout=self.timeout
            )
            
            logger.debug(f"发送请求: POST {products_url}")
            logger.debug(f"请求头: {headers}")
            logger.debug(f"请求参数: {params}")
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                try:
                    logger.info("成功获取产品列表数据")
                    return True, response.json()
                except json.JSONDecodeError:
                    logger.warning("产品列表响应不是有效的JSON")
                    return True, response.text
            else:
                logger.error(f"获取产品数据失败: HTTP {response.status_code} - {response.text}")
                # 如果是401错误，尝试刷新token并重试一次
                if response.status_code == 401:
                    logger.warning("认证失败，尝试刷新token并重试")
                    self.access_token = self._get_access_token()
                    if self.access_token:
                        headers['accessToken'] = self.access_token
                        # 重试时同样使用POST请求
                        response = session.post(
                            products_url,
                            json=params,
                            headers=headers,
                            timeout=self.timeout
                        )
                        if response.status_code == 200:
                            logger.info("刷新token后成功获取产品列表")
                            return True, response.json()
                return False, {'error': f'HTTP错误: {response.status_code}', 'response': response.text}
        except Exception as e:
            logger.error(f"获取产品数据异常: {str(e)}")
            return False, {'error': str(e)}


    # 获取FBA库存数据
    def get_fba_inventory(self, page: int = 1, page_size: int = 100, **params) -> Tuple[bool, Any]:
        """获取FBA库存数据"""
        logger.info(f"获取FBA库存数据: 页码={page}, 每页数量={page_size}")
        # 构建请求参数
        params.update({'page': page, 'pagesize': page_size})
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取FBA库存数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求FBA库存数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，避免拼接问题
        fba_inventory_url = f"{self.base_url.rstrip('/')}/fulfillment/inventory/inventoryAge/page"
        logger.debug(f"构建的FBA库存URL: {fba_inventory_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到FBA库存请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    fba_inventory_url,
                    json=params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {fba_inventory_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        logger.info("成功获取FBA库存数据")
                        return True, response.json()
                    except json.JSONDecodeError:
                        logger.warning("FBA库存响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429:
                    # 处理限流情况
                    if retry < self.max_retries:
                        logger.warning(f"FBA库存请求触发限流，重试（{retry+1}/{self.max_retries}）")
                        # 指数退避：根据重试次数增加等待时间
                        wait_time = self.retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("FBA库存请求触发限流，重试次数已达上限")
                        return False, {'error': '请求过于频繁，触发限流'}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                else:
                    logger.error(f"FBA库存请求失败: HTTP {response.status_code} - {response.text}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < self.max_retries:
                    logger.warning(f"FBA库存请求超时，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("FBA库存请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"FBA库存请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取FBA库存数据过程中发生异常: {str(e)}")
            return False, {'error': str(e)}


    # 获取市场店铺信息
    def get_marketplaces(self, page: int = 1, page_size: int = 100, **params) -> Tuple[bool, Any]:
        """获取市场店铺信息"""
        logger.info(f"获取市场店铺信息: 页码={page}, 每页数量={page_size}")
        params.update({'page': page, 'pagesize': page_size})
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取市场店铺信息前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求市场店铺数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，避免拼接问题
        marketplaces_url = f"{self.base_url.rstrip('/')}/middle/base/market/page"
        logger.debug(f"构建的市场店铺URL: {marketplaces_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到市场店铺请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    marketplaces_url,
                    json=params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {marketplaces_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        logger.info("成功获取市场店铺数据")
                        return True, response.json()
                    except json.JSONDecodeError:
                        logger.warning("市场店铺响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429:
                    # 处理限流情况
                    if retry < self.max_retries:
                        logger.warning(f"市场店铺请求触发限流，重试（{retry+1}/{self.max_retries}）")
                        # 指数退避：根据重试次数增加等待时间
                        wait_time = self.retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("市场店铺请求触发限流，重试次数已达上限")
                        return False, {'error': '请求过于频繁，触发限流'}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                else:
                    logger.error(f"市场店铺请求失败: HTTP {response.status_code} - {response.text}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < self.max_retries:
                    logger.warning(f"市场店铺请求超时，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("市场店铺请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"市场店铺请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取市场店铺数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}


    # 获取SPAD数据
    def get_sp_ad(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SPAD数据"""
        logger.info(f"获取SPAD数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID列表
        if market_ids:
            if isinstance(market_ids, list):
                request_params['marketIds'] = market_ids
            else:
                request_params['marketIds'] = [market_ids]
        
        # 添加日期范围参数
        if start_data_date:
            request_params['startDataDate'] = start_data_date
        if end_data_date:
            request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SPAD数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SPAD数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，避免拼接问题
        spad_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSpProduct/query"
        logger.debug(f"构建的SPAD数据URL: {spad_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SPAD数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    spad_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {spad_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SPAD数据")
                        # 构造包含数据和nextId的返回结构，便于上层调用处理分页
                        result = {
                            'data': response_data.get('data', []),
                            'next_id': response_data.get('extObj'),
                            'has_more': response_data.get('extObj') is not None and len(response_data.get('data', [])) > 0
                        }
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SPAD响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SPAD请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SPAD请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                else:
                    logger.error(f"SPAD请求失败: HTTP {response.status_code} - {response.text}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < self.max_retries:
                    logger.warning(f"SPAD请求超时，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SPAD请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"SPAD请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取SPAD数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}


    # 获取SPKW数据
    def get_sp_kw(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SPKW数据"""
        logger.info(f"获取SPKW数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID列表
        if market_ids:
            if isinstance(market_ids, list):
                request_params['marketIds'] = market_ids
            else:
                request_params['marketIds'] = [market_ids]
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SPKW数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SPKW数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用用户指定的请求地址
        sp_kw_url = f"{self.base_url.rstrip('/')}/operation/ads/spKeywordsPage/query"
        logger.debug(f"构建的SPKW数据URL: {sp_kw_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SPKW数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sp_kw_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sp_kw_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SPKW数据")
                        # 构造包含数据和nextId的返回结构，便于上层调用处理分页
                        result = {
                            'data': response_data.get('data', []),
                            'next_id': response_data.get('extObj'),
                            'has_more': response_data.get('extObj') is not None and len(response_data.get('data', [])) > 0
                        }
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SPKW响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SPKW请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SPKW请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                else:
                    logger.error(f"SPKW请求失败: HTTP {response.status_code} - {response.text}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < self.max_retries:
                    logger.warning(f"SPKW请求超时，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SPKW请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"SPKW请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取SPKW数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}

                
    # 在get_sp_target方法后添加以下代码
    def get_sp_placement(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SP Placement数据"""
        logger.info(f"获取SP Placement数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是单数形式marketId
        if market_ids:
            request_params['marketId'] = market_ids
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SP Placement数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SP Placement数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sp_placement_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSpPlacement/page"
        logger.debug(f"构建的SP Placement数据URL: {sp_placement_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SP Placement数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sp_placement_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sp_placement_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SP Placement数据")
                        # 根据其他方法的模式构造返回结构
                        placement_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': placement_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(placement_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SP Placement响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SP Placement请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SP Placement请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SP Placement请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SP Placement请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SP Placement请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SP Placement请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SP Placement请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取SP广告目标投放数据
    def get_sp_target(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SP Target数据"""
        logger.info(f"获取SP Target数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID列表
        if market_ids:
            if isinstance(market_ids, list):
                request_params['marketIds'] = market_ids
            else:
                request_params['marketIds'] = [market_ids]
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SP Target数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SP Target数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sp_target_url = f"{self.base_url.rstrip('/')}/operation/ads/spSearchTargetingReport/page"
        logger.debug(f"构建的SP Target数据URL: {sp_target_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SP Target数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sp_target_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sp_target_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SP Target数据")
                        # 根据get_sp_kw方法的模式修改返回结构
                        target_data_list = response_data.get('data', [])
                        
                        # 构造与get_sp_kw方法一致的返回结果结构
                        result = {
                            'data': target_data_list,  # 与get_sp_kw保持一致，使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(target_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SP Target响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SP Target请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SP Target请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                else:
                    logger.error(f"SP Target请求失败: HTTP {response.status_code} - {response.text}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < self.max_retries:
                    logger.warning(f"SP Target请求超时，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SP Target请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"SP Target请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取SP Target数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}
        return False, {'error': '未知错误'}

    
       # 在get_sp_placement方法后添加以下代码
    
    
    # 获取SP广告搜索关键词数据
    def get_sp_search_terms(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SP Search Terms数据"""
        logger.info(f"获取SP Search Terms数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是单数形式marketId
        if market_ids:
            request_params['marketId'] = market_ids
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SP Search Terms数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SP Search Terms数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sp_search_terms_url = f"{self.base_url.rstrip('/')}/operation/ads/spSearchKeywordsReport/page"
        logger.debug(f"构建的SP Search Terms数据URL: {sp_search_terms_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SP Search Terms数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sp_search_terms_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sp_search_terms_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SP Search Terms数据")
                        # 根据其他方法的模式构造返回结构
                        search_terms_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': search_terms_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(search_terms_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SP Search Terms响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SP Search Terms请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SP Search Terms请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SP Search Terms请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SP Search Terms请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SP Search Terms请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SP Search Terms请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SP Search Terms请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取SB广告关键词数据
    def get_sb_keywords(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SB Keywords数据"""
        logger.info(f"获取SB Keywords数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是单数形式marketId
        if market_ids:
            request_params['marketId'] = market_ids
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SB Keywords数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SB Keywords数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sb_keywords_url = f"{self.base_url.rstrip('/')}/operation/ads/sbKeywordsPage/query"
        logger.debug(f"构建的SB Keywords数据URL: {sb_keywords_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SB Keywords数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sb_keywords_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sb_keywords_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SB Keywords数据")
                        # 根据其他方法的模式构造返回结构
                        sb_keywords_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': sb_keywords_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(sb_keywords_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SB Keywords响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SB Keywords请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SB Keywords请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SB Keywords请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SB Keywords请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SB Keywords请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SB Keywords请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SB Keywords请求失败")
        return False, {'error': '请求失败，未知原因'}

    
    # 获取SB广告活动数据
    def get_sb_campaign(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SB Campaign数据"""
        logger.info(f"获取SB Campaign数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是单数形式marketId
        if market_ids:
            request_params['marketId'] = market_ids
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SB Campaign数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SB Campaign数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用用户指定的请求地址
        sb_campaign_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSbCampaign/query"
        logger.debug(f"构建的SB Campaign数据URL: {sb_campaign_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SB Campaign数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sb_campaign_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sb_campaign_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SB Campaign数据")
                        # 根据其他方法的模式构造返回结构
                        sb_campaign_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': sb_campaign_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(sb_campaign_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SB Campaign响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SB Campaign请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SB Campaign请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SB Campaign请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SB Campaign请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SB Campaign请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SB Campaign请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SB Campaign请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取SB广告创意数据
    def get_sb_creatives(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SB Creatives数据"""
        logger.info(f"获取SB Creatives数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是单数形式marketId
        if market_ids:
            request_params['marketId'] = market_ids
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SB Creatives数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SB Creatives数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sb_creatives_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSbCreative/page"
        logger.debug(f"构建的SB Creatives数据URL: {sb_creatives_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SB Creatives数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sb_creatives_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sb_creatives_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SB Creatives数据")
                        # 根据其他方法的模式构造返回结构
                        sb_creatives_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': sb_creatives_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(sb_creatives_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SB Creatives响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SB Creatives请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SB Creatives请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SB Creatives请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SB Creatives请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SB Creatives请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SB Creatives请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SB Creatives请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取SB广告目标投放数据
    def get_sb_targetings(self, market_ids, count=100, next_id=None, start_data_date=None, end_data_date=None, **params):
        """
        获取SB广告目标投放数据
        Args:
            market_ids: 市场ID列表
            count: 每页数量
            next_id: 分页标识
            start_data_date: 开始日期
            end_data_date: 结束日期
            **params: 其他参数
        
        Returns:
            Tuple[bool, Any]: (是否成功, 结果数据)
        """
        try:
            # 构建请求参数
            request_params = {
                'count': min(count, 100)  # 确保count不超过100
            }
            
            # 添加分页参数nextId
            if next_id is not None:
                request_params['nextId'] = next_id
            
            # 添加市场ID参数 - 根据API要求使用正确的参数格式
            if market_ids:
                # 修复参数类型错误：如果是单个市场ID，使用整数而不是列表
                if isinstance(market_ids, list) and len(market_ids) == 1:
                    request_params['marketId'] = market_ids[0]  # 使用单个整数值
                else:
                    request_params['marketId'] = market_ids
            
            # 添加日期范围参数 - 根据API要求使用startDate和endDate
            if start_data_date:
                # 将date对象转换为字符串格式
                if hasattr(start_data_date, 'strftime'):
                    request_params['startDate'] = start_data_date.strftime('%Y-%m-%d')
                else:
                    request_params['startDate'] = start_data_date
            if end_data_date:
                # 将date对象转换为字符串格式
                if hasattr(end_data_date, 'strftime'):
                    request_params['endDate'] = end_data_date.strftime('%Y-%m-%d')
                else:
                    request_params['endDate'] = end_data_date
            
            # 合并额外参数
            request_params.update(params)
            
            # 确保有有效的accessToken
            current_time = int(time.time())
            if not self.access_token or current_time >= self.token_expire_time:
                logger.debug("获取SB广告目标投放数据前需要刷新token")
                self.access_token = self._get_access_token()
                
            if not self.access_token:
                logger.error("无法获取accessToken，无法请求SB广告目标投放数据")
                return False, {'error': '无法获取访问令牌'}
            
            # 构建URL
            sb_targetings_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSbTargeting/query"
            logger.debug(f"构建的SB广告目标投放URL: {sb_targetings_url}")
            
            # 创建会话并设置请求头
            session = requests.Session()
            headers = {'Content-Type': 'application/json'}
            headers['accessToken'] = self.access_token
            logger.debug("已添加accessToken到SB广告目标投放请求头")
            
            # 使用while循环进行重试 - 与get_sb_creatives保持一致
            retry = 0
            while retry <= self.max_retries:
                try:
                    # 发送请求
                    logger.debug(f"发送请求: POST {sb_targetings_url}")
                    logger.debug(f"请求头: {headers}")
                    logger.debug(f"请求参数: {request_params}")
                    
                    response = session.post(
                        sb_targetings_url,
                        json=request_params,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    logger.debug(f"响应状态码: {response.status_code}")
                    logger.debug(f"响应内容: {response.text}")
                    
                    # 检查响应状态
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info("成功获取SB广告目标投放数据")
                            
                            # 构造与其他方法一致的返回结果结构
                            targeting_data_list = data.get('data', [])
                            result = {
                                'data': targeting_data_list,
                                'next_id': data.get('extObj'),
                                'has_more': data.get('extObj') is not None and len(targeting_data_list) > 0
                            }
                            return True, result
                        except json.JSONDecodeError:
                            logger.warning("SB广告目标投放响应不是有效的JSON")
                            return True, response.text
                    elif response.status_code == 429 or response.status_code == 509:
                        # 处理限流情况
                        if retry < self.max_retries:
                            logger.warning(f"SB广告目标投放请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                            # 根据接口限流规则：每1秒1次
                            wait_time = 1  # 固定设置为1秒
                            logger.debug(f"等待{wait_time}秒后重试")
                            time.sleep(wait_time)
                            retry += 1  # 递增重试计数
                            continue
                        else:
                            logger.error(f"SB广告目标投放请求触发限流({response.status_code})，重试次数已达上限")
                            return False, {'error': '请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                    else:
                        # 其他错误
                        logger.error(f"SB广告目标投放请求失败，状态码: {response.status_code}")
                        return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
                    
                except requests.RequestException as e:
                    logger.error(f"SB广告目标投放请求发生异常: {str(e)}")
                    if retry < self.max_retries:
                        logger.warning(f"SB广告目标投放请求异常，重试（{retry+1}/{self.max_retries}）")
                        # 指数退避：根据重试次数增加等待时间
                        wait_time = self.retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1  # 递增重试计数
                        continue
                    else:
                        logger.error("SB广告目标投放请求异常，重试次数已达上限")
                        return False, {'error': f'请求异常: {str(e)}'}
            
            # 重试次数用完
            logger.error("SB广告目标投放请求失败，重试次数已达上限")
            return False, {'error': '重试次数用完，获取数据失败'}
        
        except Exception as e:
            logger.error(f"获取SB广告目标投放数据异常: {str(e)}")
            return False, {'error': str(e)}

    
    # 在文件末尾添加以下代码
    def get_sb_placement(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SB Placement数据"""
        logger.info(f"获取SB Placement数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是单数形式marketId
        if market_ids:
            if isinstance(market_ids, list) and len(market_ids) == 1:
                request_params['marketId'] = market_ids[0]  # 单个市场ID时使用整数
            else:
                request_params['marketId'] = market_ids  # 多个市场ID时使用列表
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SB Placement数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SB Placement数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sb_placement_url = f"{self.base_url.rstrip('/')}/operation/ads/sbPlacementPage/query"
        logger.debug(f"构建的SB Placement数据URL: {sb_placement_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SB Placement数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sb_placement_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sb_placement_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SB Placement数据")
                        # 构造返回结构
                        sb_placement_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': sb_placement_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(sb_placement_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SB Placement响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SB Placement请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SB Placement请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SB Placement请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SB Placement请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SB Placement请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SB Placement请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SB Placement请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 在文件末尾添加以下代码
    def get_sb_search_terms(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SB Search Terms数据"""
        logger.info(f"获取SB Search Terms数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是单数形式marketId
        if market_ids:
            if isinstance(market_ids, list) and len(market_ids) == 1:
                request_params['marketId'] = market_ids[0]  # 单个市场ID时使用整数
            else:
                request_params['marketId'] = market_ids  # 多个市场ID时使用列表
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SB Search Terms数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SB Search Terms数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sb_search_terms_url = f"{self.base_url.rstrip('/')}/operation/ads/sbSearchKeywordsReport/page"
        logger.debug(f"构建的SB Search Terms数据URL: {sb_search_terms_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SB Search Terms数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sb_search_terms_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sb_search_terms_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SB Search Terms数据")
                        # 构造返回结构
                        sb_search_terms_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': sb_search_terms_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(sb_search_terms_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SB Search Terms响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SB Search Terms请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SB Search Terms请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SB Search Terms请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SB Search Terms请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SB Search Terms请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SB Search Terms请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SB Search Terms请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 在文件末尾添加以下代码
    def get_sd_campaign(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SD Campaign数据"""
        logger.info(f"获取SD Campaign数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是正确的参数格式
        if market_ids:
            # 根据其他方法的模式，使用正确的参数名
            if isinstance(market_ids, list) and len(market_ids) == 1:
                request_params['marketId'] = market_ids[0]  # 单个市场ID时使用整数
            else:
                request_params['marketIds'] = market_ids  # 多个市场ID时使用列表
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SD Campaign数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SD Campaign数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址 - 注意端点名称
        sd_campaign_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSdCampaigns/query"  # 修改为可能正确的端点
        logger.debug(f"构建的SD Campaign数据URL: {sd_campaign_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SD Campaign数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sd_campaign_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sd_campaign_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SD Campaign数据")
                        # 根据其他方法的模式构造返回结构
                        sd_campaign_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': sd_campaign_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(sd_campaign_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SD Campaign响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SD Campaign请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SD Campaign请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SD Campaign请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SD Campaign请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SD Campaign请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SD Campaign请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SD Campaign请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取SD Product数据
    def get_sd_product(self, market_ids=None, count=100, next_id=None, start_data_date=None, end_data_date=None, **params) -> Tuple[bool, Any]:
        """获取SD Product数据"""
        logger.info(f"获取SD Product数据: market_ids={market_ids}, count={count}, next_id={next_id}, start_data_date={start_data_date}, end_data_date={end_data_date}")
        
        # 构建请求参数
        request_params = {
            'count': min(count, 100)  # 确保count不超过100
        }
        
        # 添加分页参数nextId
        if next_id is not None:
            request_params['nextId'] = next_id
        
        # 添加市场ID参数 - 注意API需要的是正确的参数格式
        if market_ids:
            # 根据其他方法的模式，使用正确的参数名
            if isinstance(market_ids, list) and len(market_ids) == 1:
                request_params['marketId'] = market_ids[0]  # 单个市场ID时使用整数
            else:
                request_params['marketIds'] = market_ids  # 多个市场ID时使用列表
        
        # 添加日期范围参数
        if start_data_date:
            # 将date对象转换为字符串格式
            if hasattr(start_data_date, 'strftime'):
                request_params['startDataDate'] = start_data_date.strftime('%Y-%m-%d')
            else:
                request_params['startDataDate'] = start_data_date
        if end_data_date:
            # 将date对象转换为字符串格式
            if hasattr(end_data_date, 'strftime'):
                request_params['endDataDate'] = end_data_date.strftime('%Y-%m-%d')
            else:
                request_params['endDataDate'] = end_data_date
        
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取SD Product数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求SD Product数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，使用正确的接口地址
        sd_product_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSdProduct/query"
        logger.debug(f"构建的SD Product数据URL: {sd_product_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到SD Product数据请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    sd_product_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {sd_product_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取SD Product数据")
                        # 根据其他方法的模式构造返回结构
                        sd_product_data_list = response_data.get('data', [])
                        
                        # 构造与其他方法一致的返回结果结构
                        result = {
                            'data': sd_product_data_list,  # 使用'data'字段
                            'next_id': response_data.get('extObj'),  # 使用extObj作为next_id来源
                            'has_more': response_data.get('extObj') is not None and len(sd_product_data_list) > 0  # 添加has_more字段
                        }
                        
                        return True, result
                    except json.JSONDecodeError:
                        logger.warning("SD Product响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429 or response.status_code == 509:
                    # 处理限流情况 - 包括429(Too Many Requests)和509(Bandwidth Limit Exceeded)
                    if retry < self.max_retries:
                        logger.warning(f"SD Product请求触发限流({response.status_code})，重试（{retry+1}/{self.max_retries}）")
                        # 根据接口限流规则：每1秒1次
                        wait_time = 1  # 固定设置为1秒
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"SD Product请求触发限流({response.status_code})，重试次数已达上限")
                        return False, {'error': f'请求触发限流，重试次数已达上限', 'status_code': response.status_code}
                else:
                    logger.error(f"SD Product请求失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}', 'status_code': response.status_code}
            except requests.RequestException as e:
                logger.error(f"SD Product请求发生异常: {str(e)}")
                if retry < self.max_retries:
                    logger.warning(f"SD Product请求异常，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("SD Product请求异常，重试次数已达上限")
                    return False, {'error': f'请求异常: {str(e)}'}
        
        logger.error("SD Product请求失败")
        return False, {'error': '请求失败，未知原因'}


      # 获取库存分类账数据
    
    
    # 获取库存分类账明细数据
    def get_inventory_storage_ledger(self, page: int = 1, page_size: int = 100, **params) -> Tuple[bool, Any]:
        """获取库存分类账数据"""
        logger.info(f"获取库存分类账数据: 页码={page}, 每页数量={page_size}")
        # 构建请求参数
        params.update({'page': page, 'pagesize': page_size})
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取库存分类账数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求库存分类账数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，避免拼接问题
        ledger_url = f"{self.base_url.rstrip('/')}/fulfillment/inventory/storageLedger/page"
        logger.debug(f"构建的库存分类账URL: {ledger_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到库存分类账请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    ledger_url,
                    json=params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {ledger_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        logger.info("成功获取库存分类账数据")
                        return True, response.json()
                    except json.JSONDecodeError:
                        logger.warning("库存分类账响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 509:
                    # 处理限流情况
                    if retry < self.max_retries:
                        logger.warning(f"库存分类账请求触发限流，重试（{retry+1}/{self.max_retries}）")
                        # 指数退避：根据重试次数增加等待时间
                        wait_time = self.retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("库存分类账请求触发限流，重试次数已达上限")
                        return False, {'error': '请求过于频繁，触发限流'}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                else:
                    logger.error(f"库存分类账请求失败: HTTP {response.status_code} - {response.text}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < self.max_retries:
                    logger.warning(f"库存分类账请求超时，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("库存分类账请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"库存分类账请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取库存分类账数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}
        
        logger.error("库存分类账请求失败")
        return False, {'error': '请求失败，未知原因'}

    
    # 修改get_inventory_storage_ledger_detail方法，使其与get_inventory_storage_ledger方法实现一致
    def get_inventory_storage_ledger_detail(self, page: int = 1, page_size: int = 100, **params) -> Tuple[bool, Any]:
        """获取库存分类账明细数据"""
        logger.info(f"获取库存分类账明细数据: 页码={page}, 每页数量={page_size}")
        # 构建请求参数
        params.update({'page': page, 'pagesize': page_size})
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取库存分类账明细数据前需要刷新token")
            self.access_token = self._get_access_token()
            
        if not self.access_token:
            logger.error("无法获取accessToken，无法请求库存分类账明细数据")
            return False, {'error': '无法获取访问令牌'}
        
        # 直接构建完整URL，避免拼接问题
        ledger_detail_url = f"{self.base_url.rstrip('/')}/purchase/inventory/storageLedgerDetail/page"
        logger.debug(f"构建的库存分类账明细URL: {ledger_detail_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到库存分类账明细请求头")
        
        retry = 0
        while retry <= self.max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    ledger_detail_url,
                    json=params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {ledger_detail_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        logger.info("成功获取库存分类账明细数据")
                        return True, response.json()
                    except json.JSONDecodeError:
                        logger.warning("库存分类账明细响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429:
                    # 处理限流情况
                    if retry < self.max_retries:
                        logger.warning(f"库存分类账明细请求触发限流，重试（{retry+1}/{self.max_retries}）")
                        # 指数退避：根据重试次数增加等待时间
                        wait_time = self.retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("库存分类账明细请求触发限流，重试次数已达上限")
                        return False, {'error': '请求过于频繁，触发限流'}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                else:
                    logger.error(f"库存分类账明细请求失败: HTTP {response.status_code} - {response.text}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < self.max_retries:
                    logger.warning(f"库存分类账明细请求超时，重试（{retry+1}/{self.max_retries}）")
                    # 指数退避：根据重试次数增加等待时间
                    wait_time = self.retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("库存分类账明细请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"库存分类账明细请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取库存分类账明细数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}
        
        logger.error("库存分类账明细请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取交易数据
    def get_transaction(self, page=1, pagesize=100,purchaseStartDate=None, queryDateType=0, purchaseEndDate=None, **params):
        """
        获取交易数据
        
        Args:
            page: 页码
            pagesize: 每页数量
            purchaseStartDate: 开始日期（可选）
            queryDateType: 查询日期类型（可选），0：市场日期，1：标准日期
            purchaseEndDate: 结束日期（可选）
            
        Returns:
            tuple: (success_flag, data)
        """
        logger = logging.getLogger('gerpgo_client')
        logger.info(f"开始获取交易数据，页码: {page}, 每页数量: {pagesize}, 开始日期: {purchaseStartDate}, 查询日期类型: {queryDateType}, 结束日期: {purchaseEndDate}")
        
        # 构建请求参数
        params.update({
            'page': page,
            'pagesize': pagesize
        })

        # 添加可选参数
        if purchaseStartDate:
            params['purchaseStartDate'] = purchaseStartDate
            logger.info(f"添加开始日期参数: {purchaseStartDate}")
        else:
            logger.warning(f"开始日期参数为空，将获取所有历史数据")
        
        if purchaseEndDate:
            params['purchaseEndDate'] = purchaseEndDate
            logger.info(f"添加结束日期参数: {purchaseEndDate}")
        else:
            logger.warning(f"结束日期参数为空，将获取所有历史数据")
            
        if queryDateType is not None:
            params['queryDateType'] = queryDateType
            logger.info(f"添加查询日期类型参数: {queryDateType}")
        
        # 确保参数格式正确 - 可能需要添加额外的参数
        logger.info(f"最终发送到API的完整参数: {params}")
        
        # 尝试同时添加下划线格式的日期参数（作为备份）
        if purchaseStartDate and 'purchase_start_date' not in params:
            params['purchase_start_date'] = purchaseStartDate
        if purchaseEndDate and 'purchase_end_date' not in params:
            params['purchase_end_date'] = purchaseEndDate
        
        # 确保有有效的访问令牌
        if not self.access_token:
            logger.info("令牌无效，尝试刷新令牌")
            token = self._get_access_token()
            if not token:
                logger.error(f"刷新令牌失败")
                return False, {'error': f'认证失败'}
        
        # 构建URL
        url = f"{self.base_url}/finance/asset/dateRangeReports/page"
        
        # 请求头
        headers = {
            'accessToken': self.access_token,
            'Content-Type': 'application/json'
        }
        
        retry = 0
        max_retries = self.max_retries
        retry_interval = self.retry_interval
        
        while retry <= max_retries:
            try:
                logger.debug(f"发送交易数据请求，URL: {url}, 参数: {params}")
                response = requests.post(
                    url,
                    headers=headers,
                    json=params,
                    timeout=self.timeout
                )
                
                # 检查响应状态码
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # 检查API返回的code
                        if data.get('code') == 200:
                            # 获取返回数据的日期范围信息
                            rows = data['data'].get('rows', [])
                            if rows:
                                # 获取第一条和最后一条数据的日期信息（如果有）
                                first_row = rows[0]
                                last_row = rows[-1]
                                logger.info(f"成功获取交易数据，总数量: {data['data'].get('total', 0)}, 数据日期范围: 第一条数据{first_row.get('marketDate') or first_row.get('standardDate') or '未知'} - 最后一条数据{last_row.get('marketDate') or last_row.get('standardDate') or '未知'}")
                            else:
                                logger.info(f"成功获取交易数据，总数量: 0（没有数据）")
                            return True, data['data']
                        else:
                            logger.error(f"API返回错误: {data.get('messages', ['未知错误'])}")
                            return False, {'error': data.get('messages', ['未知错误'])[0]}
                    except ValueError:
                        logger.error("响应JSON解析失败")
                        return False, {'error': '响应数据格式错误'}
                elif response.status_code == 429:
                    # 处理限流
                    if retry < max_retries:
                        logger.warning(f"请求频率过高，重试（{retry+1}/{max_retries}）")
                        wait_time = retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("请求频率过高，重试次数已达上限")
                        return False, {'error': '请求频率过高'}
                elif response.status_code == 401:
                    # 处理认证失败
                    if retry < max_retries:
                        logger.warning(f"认证失败，尝试刷新令牌并重试（{retry+1}/{max_retries}）")
                        token = self._get_access_token()
                        if token:
                            headers['accessToken'] = token
                            retry += 1
                            continue
                        else:
                            logger.error(f"刷新令牌失败: {message}")
                            return False, {'error': f'认证失败: {message}'}
                    else:
                        logger.error("认证失败，重试次数已达上限")
                        return False, {'error': '认证失败'}
                elif response.status_code >= 500:
                    # 处理服务器错误
                    if retry < max_retries:
                        logger.warning(f"服务器错误，重试（{retry+1}/{max_retries}）")
                        wait_time = retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"服务器错误，状态码: {response.status_code}")
                        return False, {'error': f'服务器错误: {response.status_code}'}
                else:
                    logger.error(f"HTTP错误: {response.status_code}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < max_retries:
                    logger.warning(f"交易数据请求超时，重试（{retry+1}/{max_retries}）")
                    wait_time = retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("交易数据请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"交易数据请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取交易数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}
        
        logger.error("交易数据请求失败")
        return False, {'error': '请求失败，未知原因'}

    
    # 获取流量分析数据
    def get_traffic_analysis(self, page=1, pagesize=100, currency='YUAN', beginDate=None, endDate=None,viewType='day'):
        """
        获取流量分析数据
        
        Args:
            page: 页码
            pagesize: 每页数量
            currency: 货币类型，默认为YUAN
            beginDate: 开始日期
            endDate: 结束日期
            viewType: 视图类型，默认为day
            
        Returns:
            tuple: (success_flag, data)
        """
        logger = logging.getLogger('gerpgo_client')
        logger.info(f"开始获取流量分析数据，页码: {page}, 每页数量: {pagesize}, 货币: {currency}, 开始日期: {beginDate}, 结束日期: {endDate}")
        
        # 构建请求参数 - 注意字段名称必须与API要求一致
        request_data = {
            'currency': currency,
            'viewType': viewType,
        }
        
        # 添加必要的日期参数，确保日期格式为字符串以支持JSON序列化
        if beginDate:
            # 如果是date或datetime对象，转换为字符串格式
            if hasattr(beginDate, 'strftime'):
                request_data['beginDate'] = beginDate.strftime('%Y-%m-%d')
            else:
                request_data['beginDate'] = beginDate
            logger.info(f"添加开始日期参数: {request_data['beginDate']}")
        if endDate:
            # 如果是date或datetime对象，转换为字符串格式
            if hasattr(endDate, 'strftime'):
                request_data['endDate'] = endDate.strftime('%Y-%m-%d')
            else:
                request_data['endDate'] = endDate
            logger.info(f"添加结束日期参数: {request_data['endDate']}")
        
        # 添加分页参数到model对象中（根据其他接口的模式）
        model_params = {
            'page': page,
            'pagesize': pagesize
        }
        
        # 合并参数
        request_data.update(model_params)
        
        logger.info(f"最终请求参数: {request_data}")
        
        # 确保有有效的访问令牌
        if not self.access_token:
            logger.info("令牌无效，尝试刷新令牌")
            token = self._get_access_token()
            if not token:
                logger.error(f"刷新令牌失败")
                return False, {'error': f'认证失败'}
        
        # 构建URL - 流量分析数据API端点
        url = f"{self.base_url}/operation/sts/trafficSkuAnalysis/page"
        logger.info(f"构建的流量分析API URL: {url}")
        
        # 请求头
        headers = {
            'accessToken': self.access_token,
            'Content-Type': 'application/json'
        }
        
        retry = 0
        max_retries = self.max_retries
        retry_interval = self.retry_interval
        
        while retry <= max_retries:
            try:
                logger.info(f"发送流量分析数据请求，URL: {url}")
                logger.info(f"请求头: accessToken长度={len(self.access_token) if self.access_token else 0}")
                logger.info(f"请求体: {request_data}")
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=request_data,
                    timeout=self.timeout
                )
                
                logger.info(f"响应状态码: {response.status_code}")
                logger.info(f"响应内容: {response.text[:500]}")  # 只记录前500字符
                
                # 检查响应状态码
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # 检查API返回的code
                        if data.get('code') == 200:
                            logger.info(f"成功获取流量分析数据，总数量: {data['data'].get('total', 0)}")
                            return True, data['data']
                        else:
                            logger.error(f"API返回错误: {data.get('messages', ['未知错误'])}")
                            return False, {'error': data.get('messages', ['未知错误'])[0]}
                    except ValueError:
                        logger.error("响应JSON解析失败")
                        return False, {'error': '响应数据格式错误'}
                elif response.status_code == 429:
                    # 处理限流
                    if retry < max_retries:
                        logger.warning(f"请求频率过高，重试（{retry+1}/{max_retries}）")
                        wait_time = retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("请求频率过高，重试次数已达上限")
                        return False, {'error': '请求频率过高'}
                elif response.status_code == 401:
                    # 处理认证失败
                    if retry < max_retries:
                        logger.warning(f"认证失败，尝试刷新令牌并重试（{retry+1}/{max_retries}）")
                        token = self._get_access_token()
                        if token:
                            headers['accessToken'] = token
                            retry += 1
                            continue
                        else:
                            logger.error("刷新令牌失败")
                            return False, {'error': '认证失败'}
                    else:
                        logger.error("认证失败，重试次数已达上限")
                        return False, {'error': '认证失败'}
                elif response.status_code == 509:
                    # 为509带宽限制错误添加特殊处理
                    if retry < max_retries:
                        logger.warning(f"服务器带宽限制(509)，采用更长时间间隔重试（{retry+1}/{max_retries}）")
                        # 509错误使用更长的等待时间
                        wait_time = retry_interval * (2 ** retry) * 12.1  # 增加等待时间
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("服务器带宽限制，重试次数已达上限")
                        return False, {'error': '服务器带宽限制，请稍后再试'}
                elif response.status_code >= 500:
                    # 处理服务器错误
                    if retry < max_retries:
                        logger.warning(f"服务器错误，重试（{retry+1}/{max_retries}）")
                        wait_time = retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"服务器错误，状态码: {response.status_code}")
                        return False, {'error': f'服务器错误: {response.status_code}'}
                
                else:
                    logger.error(f"HTTP错误: {response.status_code}")
                    return False, {'error': f'HTTP错误: {response.status_code}'}
            except requests.exceptions.Timeout:
                if retry < max_retries:
                    logger.warning(f"流量分析数据请求超时，重试（{retry+1}/{max_retries}）")
                    wait_time = retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("流量分析数据请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"流量分析数据请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取流量分析数据过程中发生异常: {str(e)}")
                logger.exception("详细错误信息:")  # 记录完整的异常堆栈
                return False, {'error': str(e)}
        
        logger.error("流量分析数据请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取FBA库存数据
    def get_fba_inventory_page(self, page: int = 1, pagesize: int = 100, **params) -> Tuple[bool, Any]:
        """
        获取FBA库存数据（通过/purchase/store/fbaInventory/page端点）
        
        Args:
            page: 页码，默认为1
            pagesize: 每页数量，默认为100
            **params: 额外的请求参数
            
        Returns:
            Tuple[bool, Any]: 成功状态和响应数据
        """
        logger.info(f"获取FBA库存数据(新版): 页码={page}, 每页数量={pagesize}")
        # 构建请求参数
        request_params = {'page': page, 'pagesize': pagesize}
        # 合并额外参数
        request_params.update(params)
        
        # 确保有有效的accessToken
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expire_time:
            logger.debug("获取FBA库存数据前需要刷新token")
            self.access_token = self._get_access_token()
        
        # 直接构建完整URL，避免拼接问题
        fba_inventory_url = f"{self.base_url.rstrip('/')}/purchase/store/fbaInventory/page/V2"
        logger.debug(f"构建的FBA库存URL: {fba_inventory_url}")
        
        # 使用session直接发送请求
        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        
        # 添加accessToken到请求头
        headers['accessToken'] = self.access_token
        logger.debug("已添加accessToken到FBA库存请求头")
        
        retry = 0
        max_retries = self.max_retries
        retry_interval = self.retry_interval
        
        while retry <= max_retries:
            try:
                # 使用POST请求，参数放在请求体中
                response = session.post(
                    fba_inventory_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"发送请求: POST {fba_inventory_url}")
                logger.debug(f"请求头: {headers}")
                logger.debug(f"请求参数: {request_params}")
                logger.debug(f"响应状态码: {response.status_code}")
                logger.debug(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取FBA库存数据(新版)")
                        return True, response_data
                    except json.JSONDecodeError:
                        logger.warning("FBA库存响应不是有效的JSON")
                        return True, response.text
                elif response.status_code == 429:
                    # 处理限流情况
                    if retry < max_retries:
                        logger.warning(f"FBA库存请求触发限流，重试（{retry+1}/{max_retries}）")
                        # 指数退避：根据重试次数增加等待时间
                        wait_time = retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("FBA库存请求触发限流，重试次数已达上限")
                        return False, {'error': '请求过于频繁，触发限流'}
                elif response.status_code == 401:
                    # 认证失败，尝试刷新token并重试一次
                    if retry < 1:  # 只重试一次token刷新
                        logger.warning("认证失败，尝试刷新token并重试")
                        self.access_token = self._get_access_token()
                        if self.access_token:
                            headers['accessToken'] = self.access_token
                            retry += 1
                            continue
                elif response.status_code == 509:
                    # 特殊处理带宽限制错误
                    if retry < max_retries:
                        logger.warning(f"服务器带宽限制，重试（{retry+1}/{max_retries}）")
                        wait_time = retry_interval * (2 ** retry) * 7  # 509错误额外乘以7倍
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("服务器带宽限制，重试次数已达上限")
                        return False, {'error': '服务器带宽限制，请稍后再试'}
                elif response.status_code >= 500:
                    # 处理服务器错误
                    if retry < max_retries:
                        logger.warning(f"服务器错误，重试（{retry+1}/{max_retries}）")
                        wait_time = retry_interval * (2 ** retry)
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error(f"服务器错误，状态码: {response.status_code}")
                        return False, {'error': f'服务器错误: {response.status_code}'}
                else:
                    logger.error(f"HTTP错误: {response.status_code}")
                    return False, {'error': f'HTTP错误: {response.status_code}', 'response': response.text}
            except requests.exceptions.Timeout:
                if retry < max_retries:
                    logger.warning(f"FBA库存请求超时，重试（{retry+1}/{max_retries}）")
                    wait_time = retry_interval * (2 ** retry)
                    logger.debug(f"等待{wait_time}秒后重试")
                    time.sleep(wait_time)
                    retry += 1
                    continue
                else:
                    logger.error("FBA库存请求超时，重试次数已达上限")
                    return False, {'error': '请求超时'}
            except requests.exceptions.RequestException as e:
                logger.error(f"FBA库存请求异常: {str(e)}")
                return False, {'error': str(e)}
            except Exception as e:
                logger.error(f"获取FBA库存数据过程中发生异常: {str(e)}")
                return False, {'error': str(e)}
        
        logger.error("FBA库存数据请求失败")
        return False, {'error': '请求失败，未知原因'}


    # 获取月度仓储费数据
    def get_month_storage_fee(self,page:int=1,pagesize:int=100,**params) -> Tuple[bool, Any]:
        """
        获取月度仓储费数据（端点：/finance/asset/storageFee/page）

        Args:
            page (int, optional): 页码，默认值为1。
            pagesize (int, optional): 每页数据量，默认值为100。
            **params: 额外的请求参数

        Returns:
            Tuple[bool, Any]: 包含请求成功状态和数据的元组。
        """
        
        logger.info(f"获取月度仓储费数据，页码: {page}, 每页数据量: {pagesize}, 额外参数: {params}") # 日志中记录请求参数

        # 构建请求参数
        params = {
            'page': page,
            'pagesize': pagesize,
            'year': params.get('year'),
            'month': params.get('month')
        }

        # 确保acessToken有效
        current_time = int(time.time()) # 当前时间戳
        if not self.access_token or current_time >= self.token_expire_time: # 如果token不存在或过期
            logger.warning("accessToken过期或不存在，尝试刷新token")
            self.access_token = self._get_access_token() # 刷新token

        # 构建请求url
        storage_fee_url = f"{self.base_url.rstrip('/')}/finance/asset/storageFee/page"
        logger.debug(f"构建请求url: {storage_fee_url}") # 日志中记录请求url

        # 使用session发送请求
        session = requests.Session()
        headers = {
            'Content-Type': 'application/json',
            'accessToken': self.access_token
        }
        logger.debug("已添加accessToken到月度仓储费请求头")

        # 开始请求api接口
        retry = 0
        max_retries = self.max_retries
        retry_interval = self.retry_interval

        while retry <= max_retries:
            try:
                response = session.post(
                    url=storage_fee_url, # 月度仓储费api接口url
                    headers=headers, # 请求头
                    json=params, # 请求参数
                    timeout=self.timeout # 请求超时时间
                )

                logger.debug(f"发送请求：POST {storage_fee_url}，参数: {params}")
                logger.debug(f"响应状态码: {response.status_code}")
                
                # 处理响应内容
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info("成功获取月度仓储费数据")
                        return True,response_data # 返回json数据
                    except json.JSONDecodeError:
                        logger.error("响应内容不是有效的JSON格式")
                        return True, response.text # 返回原始文本
                elif response.status_code == 429:
                        # 处理限流情况
                        if retry < max_retries: 
                            logger.warning(f"FBA库存请求触发限流，重试（{retry+1}/{max_retries}）")
                            wait_time = retry_interval * (2 ** retry)
                            logger.warning(f"收到429错误，等待{wait_time}秒后重试")
                            time.sleep(wait_time)
                            retry += 1
                            continue
                        else:
                            logger.error("收到429错误，重试次数已达上限")
                            return False, {'error': '请求被限流'}
                elif response.status_code == 509:
                            if retry < max_retries:
                                logger.warning(f"服务器带宽限制，重试（{retry+1}/{max_retries}）")
                                wait_time = retry_interval * (2 ** retry) * 7  # 509错误额外乘以7倍
                                logger.debug(f"等待{wait_time}秒后重试")
                                time.sleep(wait_time)
                                retry += 1
                                continue
                            else:
                                logger.error("服务器带宽限制，重试次数已达上限")
                                return False, {'error': '服务器带宽限制，请稍后再试'}
                else:
                    logger.error(f"获取月度仓储费数据失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}'}
            except requests.RequestException as e:
                logger.error(f"请求月度仓储费数据时发生错误: {e}")
                return False, {'error': f'请求失败，错误信息: {str(e)}'}


    # 获取财务利润分析数据
    def get_financial_analysis(self, page: int = 1, pagesize: int = 100, type: str='MSKU',
        showCurrencyType: str = 'YUAN' ,beginDate: datetime.date = None, endDate: datetime.date = None) -> Tuple[bool, Any]:
        """
        获取财务利润数据

        Args:
            page (int, optional): 页码，默认值为 1
            pagesize (int, optional): 每页数据量，默认值为 100
            type (str, optional): 查询类型 [market，category，father_asin，asin，spu，sku，msku]，默认值为 'MSKU'
            showCurrencyType (str, optional): 货币类型，默认值为 'YUAN'
            beginDate (datetime.date, optional): 开始日期，默认值为 None
            endDate (datetime.date, optional): 结束日期，默认值为 None
        """

        logger = logging.getLogger(__name__)
        logger.info(f"获取财务利润分析数据，查询类型: {type}，页码: {page}，每页数据量: {pagesize}，货币类型: {showCurrencyType}，开始日期: {beginDate}，结束日期: {endDate}")

        # 构建必要请求参数
        params = {
            'type': type,
            'page': page,
            'pagesize': pagesize,
            'showCurrencyType': showCurrencyType        
            }

        # 添加可选参数
        if beginDate:
            params['beginDate'] = beginDate.strftime('%Y-%m-%d')
        if endDate:
            params['endDate'] = endDate.strftime('%Y-%m-%d')

        # 确保访问令牌有效
        current_time = time.time()
        if not self.access_token or current_time >= self.token_expire_time:
            logger.info("令牌无效，尝试刷新令牌")
            self.access_token = self._get_access_token()
            if not self.access_token:
                logger.error(f"刷新令牌失败")
                return False, {'error': f'认证失败'}

        # 构建请求url
        url = f"{self.base_url}/operation/sts/saleProfit/page"

        # 构建请求头
        session = requests.Session()
        headers = {
            'accessToken': self.access_token,
            'Content-Type': 'application/json'
        }


        # 构建重试机制
        retry = 0
        max_retries = self.max_retries
        retry_interval = self.retry_interval

        while retry <= max_retries:
            try:
                logger.debug(f"发生利润分析数据请求")
                response = session.post(
                    url,
                    headers=headers,
                    json=params, # 以json格式发送请求参数
                    timeout=self.timeout
                )

                # 检查响应码
                if response.status_code == 200:
                    logger.info("成功获取利润分析数据")
                    return True, response.json()
                elif response.status_code == 509:
                    if retry < max_retries:
                        logger.warning(f"服务器带宽限制，重试（{retry+1}/{max_retries}）")
                        wait_time = retry_interval * (2 ** retry+1) * 6.1  # 509错误额外乘以7倍
                        logger.debug(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
                        retry += 1
                        continue
                    else:
                        logger.error("服务器带宽限制，重试次数已达上限")
                        return False, {'error': '服务器带宽限制，请稍后再试'}
                else:
                    logger.error(f"获取利润分析数据失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}'}
            except requests.RequestException as e:
                logger.error(f"请求利润分析数据时发生错误: {e}")
                return False, {'error': f'请求失败，错误信息: {str(e)}'}


    def get_currency_rate(self, page: int = 1, pagesize: int = 500) -> Any:
        """
        获取汇率数据
        Args:
            page (int, optional): 页码，默认值为 1
            pagesize (int, optional): 每页数据量，默认值为 500
        """
        logger = logging.getLogger(__name__)
        logger.info(f"获取汇率数据，页码: {page}，每页数据量: {pagesize}")

        #确保访问令牌有效
        current_time = time.time()
        if not self.access_token or current_time >= self.token_expire_time:
            logger.info("令牌无效，尝试刷新令牌")
            self.access_token = self._get_access_token()
            if not self.access_token:
                logger.error(f"刷新令牌失败")
                return False, {'error': f'认证失败'}

        # 构建请求url
        url = f"{self.base_url}/middle/base/rate/page"

        # 构建请求头
        session = requests.Session()
        headers = {
            'accessToken': self.access_token,
            'Content-Type': 'application/json'
        }

        # 构建重试机制
        retry = 0
        max_retries = self.max_retries
        retry_interval = self.retry_interval

        while retry <= max_retries:
            try:
                logger.debug(f"发生汇率数据请求")
                response = session.get(
                    url,
                    headers=headers,
                    params={'page': page, 'pagesize': pagesize},
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    logger.info("成功获取汇率数据")
                    return True, response.json()
                else:
                    logger.error(f"获取汇率数据失败，状态码: {response.status_code}")
                    return False, {'error': f'请求失败，状态码: {response.status_code}'}
            except requests.RequestException as e:
                logger.error(f"请求汇率数据时发生错误: {e}")
                return False, {'error': f'请求失败，错误信息: {str(e)}'}
            