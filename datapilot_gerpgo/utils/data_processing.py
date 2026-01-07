"""
数据处理工具函数
"""
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    清洗数据，去除空值和无用字段
    
    Args:
        data: 原始数据字典
        
    Returns:
        Dict[str, Any]: 清洗后的数据字典
    """
    if not isinstance(data, dict):
        return data
    
    cleaned_data = {}
    for key, value in data.items():
        # 跳过None、空字符串等
        if value is None or value == '' or (isinstance(value, (list, dict)) and len(value) == 0):
            continue
        
        # 递归清洗嵌套数据
        if isinstance(value, dict):
            cleaned_data[key] = clean_data(value)
        elif isinstance(value, list):
            cleaned_data[key] = [clean_data(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned_data[key] = value
    
    return cleaned_data


def transform_date_format(date_str: str, from_format: str = '%Y-%m-%d %H:%M:%S', to_format: str = '%Y-%m-%dT%H:%M:%SZ') -> Optional[str]:
    """
    转换日期格式
    
    Args:
        date_str: 原始日期字符串
        from_format: 输入日期格式
        to_format: 输出日期格式
        
    Returns:
        Optional[str]: 转换后的日期字符串，如果转换失败则返回None
    """
    try:
        date_obj = datetime.strptime(date_str, from_format)
        return date_obj.strftime(to_format)
    except (ValueError, TypeError) as e:
        logger.error(f"日期格式转换失败: {date_str}, 错误: {str(e)}")
        return None


def parse_date(date_str: str, formats: Optional[List[str]] = None) -> Optional[datetime]:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串
        formats: 可能的日期格式列表
        
    Returns:
        Optional[datetime]: 解析后的日期时间对象，如果解析失败则返回None
    """
    if formats is None:
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d'
        ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    
    logger.error(f"无法解析日期: {date_str}")
    return None


def convert_currency(value: Any, from_currency: str, to_currency: str, exchange_rate: float = 1.0) -> float:
    """
    转换货币
    
    Args:
        value: 金额
        from_currency: 原始货币
        to_currency: 目标货币
        exchange_rate: 汇率
        
    Returns:
        float: 转换后的金额
    """
    try:
        if from_currency == to_currency:
            return float(value)
        
        return float(value) * exchange_rate
    except (ValueError, TypeError) as e:
        logger.error(f"货币转换失败: {value}, 错误: {str(e)}")
        return 0.0


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    计算百分比变化
    
    Args:
        old_value: 旧值
        new_value: 新值
        
    Returns:
        float: 百分比变化
    """
    try:
        if old_value == 0:
            return 0.0
        
        return ((new_value - old_value) / old_value) * 100
    except (ValueError, TypeError) as e:
        logger.error(f"计算百分比变化失败: 旧值={old_value}, 新值={new_value}, 错误: {str(e)}")
        return 0.0


def aggregate_data(data_list: List[Dict[str, Any]], group_by: str, aggregate_fields: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """
    聚合数据
    
    Args:
        data_list: 数据列表
        group_by: 分组字段
        aggregate_fields: 聚合字段配置，格式为 {字段名: 聚合函数}
        
    Returns:
        Dict[str, Dict[str, Any]]: 聚合结果
    """
    result = {}
    
    for item in data_list:
        if group_by not in item:
            continue
        
        group_key = item[group_by]
        
        if group_key not in result:
            result[group_key] = {}
            # 初始化聚合结果
            for field, func in aggregate_fields.items():
                result[group_key][f'{field}_{func}'] = 0 if func in ['sum', 'count'] else None
        
        # 执行聚合
        for field, func in aggregate_fields.items():
            if field not in item or item[field] is None:
                continue
            
            try:
                value = float(item[field])
                
                if func == 'sum':
                    result[group_key][f'{field}_sum'] += value
                elif func == 'avg':
                    # 对于平均值，需要记录总和和计数
                    sum_key = f'{field}_sum'
                    count_key = f'{field}_count'
                    
                    if sum_key not in result[group_key]:
                        result[group_key][sum_key] = 0
                    if count_key not in result[group_key]:
                        result[group_key][count_key] = 0
                    
                    result[group_key][sum_key] += value
                    result[group_key][count_key] += 1
                elif func == 'max':
                    current_value = result[group_key][f'{field}_max']
                    if current_value is None or value > current_value:
                        result[group_key][f'{field}_max'] = value
                elif func == 'min':
                    current_value = result[group_key][f'{field}_min']
                    if current_value is None or value < current_value:
                        result[group_key][f'{field}_min'] = value
                elif func == 'count':
                    result[group_key][f'{field}_count'] += 1
            except (ValueError, TypeError) as e:
                logger.error(f"数据聚合失败: 字段={field}, 值={item[field]}, 错误: {str(e)}")
    
    # 计算平均值
    for group_key, group_data in result.items():
        for field, func in aggregate_fields.items():
            if func == 'avg':
                sum_key = f'{field}_sum'
                count_key = f'{field}_count'
                
                if sum_key in group_data and count_key in group_data and group_data[count_key] > 0:
                    group_data[f'{field}_avg'] = group_data[sum_key] / group_data[count_key]
                    # 清理临时字段
                    del group_data[sum_key]
                    del group_data[count_key]
    
    return result


def batch_process_data(data_list: List[Dict[str, Any]], process_func: callable, batch_size: int = 100) -> List[Any]:
    """
    批量处理数据
    
    Args:
        data_list: 数据列表
        process_func: 处理函数
        batch_size: 批次大小
        
    Returns:
        List[Any]: 处理结果列表
    """
    results = []
    
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i + batch_size]
        
        try:
            batch_results = process_func(batch)
            
            if isinstance(batch_results, list):
                results.extend(batch_results)
            else:
                results.append(batch_results)
                
            logger.debug(f"处理批次 {i // batch_size + 1}, 处理了 {len(batch)} 条数据")
            
        except Exception as e:
            logger.error(f"批量处理数据失败: 批次={i // batch_size + 1}, 错误: {str(e)}")
            # 可以选择继续处理下一批或抛出异常
            
    return results


def filter_data(data_list: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    过滤数据
    
    Args:
        data_list: 数据列表
        filters: 过滤条件，格式为 {字段名: 过滤值}
        
    Returns:
        List[Dict[str, Any]]: 过滤后的数据列表
    """
    filtered_data = []
    
    for item in data_list:
        match = True
        
        for field, filter_value in filters.items():
            if field not in item:
                match = False
                break
            
            item_value = item[field]
            
            # 处理不同类型的过滤
            if isinstance(filter_value, dict):
                # 支持范围过滤等复杂过滤
                if 'gte' in filter_value and item_value < filter_value['gte']:
                    match = False
                    break
                if 'lte' in filter_value and item_value > filter_value['lte']:
                    match = False
                    break
                if 'gt' in filter_value and item_value <= filter_value['gt']:
                    match = False
                    break
                if 'lt' in filter_value and item_value >= filter_value['lt']:
                    match = False
                    break
                if 'contains' in filter_value and filter_value['contains'] not in str(item_value):
                    match = False
                    break
            elif isinstance(filter_value, (list, tuple)):
                # 列表值表示"在...中"
                if item_value not in filter_value:
                    match = False
                    break
            else:
                # 精确匹配
                if item_value != filter_value:
                    match = False
                    break
        
        if match:
            filtered_data.append(item)
    
    return filtered_data


def sort_data(data_list: List[Dict[str, Any]], sort_by: str, reverse: bool = False) -> List[Dict[str, Any]]:
    """
    排序数据
    
    Args:
        data_list: 数据列表
        sort_by: 排序字段
        reverse: 是否降序
        
    Returns:
        List[Dict[str, Any]]: 排序后的数据列表
    """
    try:
        # 处理嵌套字段
        if '.' in sort_by:
            def get_sort_key(item):
                keys = sort_by.split('.')
                value = item
                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return None
                return value
            
            return sorted(data_list, key=get_sort_key, reverse=reverse)
        else:
            # 普通字段排序
            return sorted(data_list, key=lambda x: x.get(sort_by), reverse=reverse)
    except Exception as e:
        logger.error(f"数据排序失败: {str(e)}")
        return data_list


def convert_to_dataframe(data_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    将数据列表转换为pandas DataFrame
    
    Args:
        data_list: 数据列表
        
    Returns:
        pd.DataFrame: 转换后的DataFrame
    """
    try:
        df = pd.DataFrame(data_list)
        return df
    except Exception as e:
        logger.error(f"转换数据到DataFrame失败: {str(e)}")
        return pd.DataFrame()


def export_to_excel(df: pd.DataFrame, file_path: str, sheet_name: str = 'Sheet1') -> bool:
    """
    导出数据到Excel文件
    
    Args:
        df: pandas DataFrame
        file_path: 文件路径
        sheet_name: 工作表名称
        
    Returns:
        bool: 是否导出成功
    """
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"数据已导出到Excel文件: {file_path}")
        return True
    except Exception as e:
        logger.error(f"导出数据到Excel失败: {str(e)}")
        return False


def export_to_json(data: Any, file_path: str, indent: int = 2) -> bool:
    """
    导出数据到JSON文件
    
    Args:
        data: 要导出的数据
        file_path: 文件路径
        indent: 缩进空格数
        
    Returns:
        bool: 是否导出成功
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        
        logger.info(f"数据已导出到JSON文件: {file_path}")
        return True
    except Exception as e:
        logger.error(f"导出数据到JSON失败: {str(e)}")
        return False