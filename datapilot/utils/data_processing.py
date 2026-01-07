"""数据处理工具模块

该模块提供数据清洗、转换、聚合和格式化等功能，用于处理从API获取的数据。
"""
import json
import re
from datetime import datetime, date
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def clean_data(data, fields=None):
    """清洗数据，移除空值或无效值
    
    参数:
        data: 要清洗的数据（字典或列表）
        fields: 要检查的字段列表，如果为None则检查所有字段
    
    返回:
        清洗后的数据
    """
    try:
        if isinstance(data, list):
            # 清洗列表中的每个元素
            return [clean_data(item, fields) for item in data if item is not None]
        elif isinstance(data, dict):
            # 清洗字典中的每个字段
            cleaned_dict = {}
            for key, value in data.items():
                # 如果指定了字段列表，则只处理指定的字段
                if fields is None or key in fields:
                    # 递归清洗嵌套数据
                    if isinstance(value, (dict, list)):
                        cleaned_value = clean_data(value)
                        if cleaned_value:
                            cleaned_dict[key] = cleaned_value
                    # 移除空值
                    elif value is not None and value != '':
                        cleaned_dict[key] = value
            return cleaned_dict
        else:
            # 对于基本类型，直接返回
            return data
    except Exception as e:
        logger.error(f"数据清洗失败: {str(e)}")
        return data

def transform_date_format(date_str, from_format='%Y%m%d', to_format='%Y-%m-%d'):
    """转换日期格式
    
    参数:
        date_str: 日期字符串
        from_format: 原始日期格式
        to_format: 目标日期格式
    
    返回:
        转换后的日期字符串，转换失败则返回原始字符串
    """
    if not date_str:
        return None
    
    try:
        # 尝试解析日期并重新格式化
        date_obj = datetime.strptime(str(date_str), from_format)
        return date_obj.strftime(to_format)
    except ValueError:
        # 如果解析失败，尝试其他常见格式
        common_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
        for fmt in common_formats:
            try:
                date_obj = datetime.strptime(str(date_str), fmt)
                return date_obj.strftime(to_format)
            except ValueError:
                continue
        
        logger.warning(f"无法解析日期格式: {date_str}")
        return date_str
    except Exception as e:
        logger.error(f"日期格式转换失败: {str(e)}")
        return date_str

def aggregate_data(data_list, group_by_field, aggregate_fields, aggregate_func='sum'):
    """聚合数据
    
    参数:
        data_list: 数据列表
        group_by_field: 分组字段
        aggregate_fields: 要聚合的字段列表
        aggregate_func: 聚合函数，支持'sum', 'avg', 'min', 'max', 'count'
    
    返回:
        聚合后的结果字典
    """
    try:
        if not data_list or not group_by_field or not aggregate_fields:
            return {}
        
        # 使用pandas进行数据聚合
        df = pd.DataFrame(data_list)
        
        # 确保分组字段存在
        if group_by_field not in df.columns:
            logger.error(f"分组字段 '{group_by_field}' 不存在")
            return {}
        
        # 确保所有聚合字段存在
        for field in aggregate_fields:
            if field not in df.columns:
                logger.warning(f"聚合字段 '{field}' 不存在")
                aggregate_fields.remove(field)
        
        if not aggregate_fields:
            return {}
        
        # 聚合数据
        agg_dict = {field: aggregate_func for field in aggregate_fields}
        result_df = df.groupby(group_by_field).agg(agg_dict).reset_index()
        
        # 转换为字典格式
        result = {}
        for _, row in result_df.iterrows():
            group_key = row[group_by_field]
            result[group_key] = {}
            for field in aggregate_fields:
                result[group_key][field] = row[field]
        
        return result
    except Exception as e:
        logger.error(f"数据聚合失败: {str(e)}")
        return {}

def format_currency(value, currency='USD', precision=2):
    """格式化货币值
    
    参数:
        value: 货币值
        currency: 货币类型
        precision: 小数位数
    
    返回:
        格式化后的货币字符串
    """
    try:
        # 尝试将值转换为数字
        num_value = float(value) if value is not None else 0
        
        # 根据货币类型选择符号和格式
        currency_formats = {
            'USD': '${:,.{}f}',
            'EUR': '€{:,.{}f}',
            'GBP': '£{:,.{}f}',
            'CNY': '¥{:,.{}f}',
        }
        
        fmt = currency_formats.get(currency.upper(), '{:,.{}f}')
        return fmt.format(num_value, precision)
    except Exception as e:
        logger.error(f"货币格式化失败: {str(e)}")
        return str(value)

def parse_csv_data(csv_content, delimiter=','):
    """解析CSV数据
    
    参数:
        csv_content: CSV内容字符串
        delimiter: 分隔符
    
    返回:
        解析后的数据列表
    """
    try:
        # 使用pandas解析CSV数据
        from io import StringIO
        df = pd.read_csv(StringIO(csv_content), delimiter=delimiter)
        
        # 转换为字典列表
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"CSV数据解析失败: {str(e)}")
        return []

def normalize_keyword_text(keyword):
    """标准化关键词文本
    
    参数:
        keyword: 关键词文本
    
    返回:
        标准化后的关键词文本
    """
    if not keyword:
        return ''
    
    try:
        # 转换为小写
        keyword = keyword.lower()
        
        # 移除多余的空格
        keyword = re.sub(r'\s+', ' ', keyword).strip()
        
        # 移除特殊字符（保留字母、数字、空格和连字符）
        keyword = re.sub(r'[^a-zA-Z0-9\s-]', '', keyword)
        
        return keyword
    except Exception as e:
        logger.error(f"关键词标准化失败: {str(e)}")
        return keyword

def calculate_metrics(data, impressions_field='impressions', clicks_field='clicks', cost_field='cost', conversions_field='conversions'):
    """计算广告效果指标
    
    参数:
        data: 包含广告数据的字典或字典列表
        impressions_field: 曝光数字段名
        clicks_field: 点击数字段名
        cost_field: 花费字段名
        conversions_field: 转换数字段名
    
    返回:
        添加了CTR、CPC、CPA和ROAS等指标的数据
    """
    try:
        if isinstance(data, list):
            # 处理列表数据
            return [calculate_metrics(item, impressions_field, clicks_field, cost_field, conversions_field) for item in data]
        elif isinstance(data, dict):
            # 处理单个字典数据
            result = data.copy()
            
            # 获取所需字段的值
            impressions = float(data.get(impressions_field, 0))
            clicks = float(data.get(clicks_field, 0))
            cost = float(data.get(cost_field, 0))
            conversions = float(data.get(conversions_field, 0))
            
            # 计算CTR (Click-Through Rate)
            if impressions > 0:
                result['ctr'] = (clicks / impressions) * 100
            else:
                result['ctr'] = 0
            
            # 计算CPC (Cost Per Click)
            if clicks > 0:
                result['cpc'] = cost / clicks
            else:
                result['cpc'] = 0
            
            # 计算CPA (Cost Per Acquisition)
            if conversions > 0:
                result['cpa'] = cost / conversions
            else:
                result['cpa'] = 0
            
            # 计算转化率
            if clicks > 0:
                result['conversion_rate'] = (conversions / clicks) * 100
            else:
                result['conversion_rate'] = 0
            
            # 如果有销售额字段，计算ROAS
            if 'sales' in data and cost > 0:
                sales = float(data['sales'])
                result['roas'] = sales / cost
            
            return result
        else:
            return data
    except Exception as e:
        logger.error(f"指标计算失败: {str(e)}")
        return data