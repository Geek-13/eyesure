"""
视图函数定义
"""
from audioop import add
import math
import logging
import json
from tokenize import group
import pytz # 时区库
from datetime import datetime, date,timedelta 
from django.shortcuts import render
from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.db.models import Q  # 添加Q对象导入
from decimal import Decimal
from dateutil import parser
from dateutil.relativedelta import relativedelta # 用于日期计算
from .models import (Product, SyncLog, Inventory,Market,SellerMarketplace,AdsSpProduct,
                    AdsSpKeyword,AdsSpTarget,AdsSpPlacement,AdsSpSearchTerms,AdsSbSearchTerms,
                    AdsSbKeyword, AdsSbCampaign,AdsSbCreative,AdsSbTargeting,AdsSbPlacement,
                    AdsSdCampaign,AdsSdProduct,InventoryStorageLedger,InventoryStorageLedgerDetail,Transaction
                    ,TrafficAnalysis,FBAInventory,MonStorageFee,ProfitAnalysis,CurrencyRate)
from .serializers import (
    ProductSerializer,
    SyncLogSerializer, SyncRequestSerializer, StatusSerializer,SPADDataRequestSerializer,SPKWDataRequestSerializer,
    SPTargetDataRequestSerializer,SPPlacementDataRequestSerializer,SPSearchTermsDataRequestSerializer,SBKWDataRequestSerializer,
    SBCampainDataRequestSerializer,SBCreativeDataRequestSerializer,SBTargetingDataRequestSerializer,SBPlacementDataRequestSerializer,
    SBSearchTermsDataRequestSerializer,SDSCampaignDataRequestSerializer,SDProductDataRequestSerializer,InventoryStorageLedgerRequestSerializer,
    InventoryStorageLedgerDetailRequestSerializer,TransactionRequestSerializer,TrafficAnalysisRequestSerializer,FBAInventorySyncRequestSerializer
    ,MonStorageFeeRequestSerializer,ProfitAnalysisRequestSerializer,SalesForecastRequestSerializer,CurrencyRateRequestSerializer
)
from .services.gerpgo_client import GerpgoAPIClient
from django.core.cache import cache  # 导入缓存模块

# 同步日志视图
logger = logging.getLogger(__name__)

# 解析日期函数
def parse_date_string(date_str):
    """
    通用日期解析函数，尝试解析各种格式的日期字符串，支持意大利语月份缩写
    
    Args:
        date_str: 日期字符串
    
    Returns:
        datetime对象，解析失败返回None
    """
    if not date_str:
        return None
    
    # 意大利语月份缩写映射到英语月份缩写
    italian_months = {
        'gen': 'jan',  # Gennaio (1月)
        'feb': 'feb',  # Febbraio (2月)
        'mar': 'mar',  # Marzo (3月)
        'apr': 'apr',  # Aprile (4月)
        'mag': 'may',  # Maggio (5月)
        'giu': 'jun',  # Giugno (6月)
        'lug': 'jul',  # Luglio (7月)
        'ago': 'aug',  # Agosto (8月)
        'set': 'sep',  # Settembre (9月)
        'ott': 'oct',  # Ottobre (10月)
        'nov': 'nov',  # Novembre (11月)
        'dic': 'dec'   # Dicembre (12月)
    }
    
    try:
        # 检查并替换意大利语月份缩写
        date_str_lower = str(date_str).lower()
        for it_month, en_month in italian_months.items():
            # 确保只替换完整的月份缩写
            import re
            date_str_lower = re.sub(r'\b' + it_month + r'\b', en_month, date_str_lower)
        
        # 使用dateutil.parser尝试解析各种格式，设置fuzzy=True以提高成功率
        parsed_date = parser.parse(date_str_lower, fuzzy=True)
        
        # 确保日期有时区信息
        if parsed_date.tzinfo:
            # 如果有时区信息，转换为UTC时区
            parsed_date = parsed_date.astimezone(pytz.UTC)
        else:
            parsed_date = timezone.make_aware(parsed_date, pytz.UTC)
        
        return parsed_date

    except (ValueError, TypeError) as e:
        logger.error(f"日期解析失败: {date_str}, 错误: {str(e)}")
        return None

# 基础视图集
class BaseModelViewSet(viewsets.ModelViewSet):
    """基础视图集，提供通用功能"""
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        """创建对象时设置创建者"""
        serializer.save()
        
    def perform_update(self, serializer):
        """更新对象时设置更新时间"""
        serializer.save()

# 产品视图集
class ProductViewSet(BaseModelViewSet):
    """产品视图集"""
    queryset = Product.objects.all().order_by('-updated_at')
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        """过滤查询集"""
        queryset = super().get_queryset()
        
        # 过滤参数
        sku = self.request.query_params.get('sku', None)
        category = self.request.query_params.get('category', None)
        brand = self.request.query_params.get('brand', None)
        status = self.request.query_params.get('status', None)
        
        if sku:
            queryset = queryset.filter(sku__icontains=sku)
        if category:
            queryset = queryset.filter(category__icontains=category)
        if brand:
            queryset = queryset.filter(brand__icontains=brand)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset


class ProductListAPIView(generics.ListAPIView):
    """产品列表API视图"""
    queryset = Product.objects.all().order_by('-updated_at')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


class ProductDetailAPIView(generics.RetrieveAPIView):
    """产品详情API视图"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


# 同步日志视图集
class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """同步日志视图集"""
    queryset = SyncLog.objects.all().order_by('-start_time')
    serializer_class = SyncLogSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """过滤查询集"""
        queryset = super().get_queryset()
        
        # 过滤参数
        sync_type = self.request.query_params.get('sync_type', None)
        status = self.request.query_params.get('status', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        if status:
            queryset = queryset.filter(status=status)
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__lte=end_date)
        
        return queryset


# 检查API状态
@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    """API状态检查"""
    try:
        # 检查数据库连接
        db_status = 'ok'
        try:
            Product.objects.count()
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        # 检查Gerpgo API连接
        gerpgo_status = 'ok'
        try:
            client = GerpgoAPIClient(
                appId=settings.GERPGO_APP_ID,
                appKey=settings.GERPGO_APP_KEY,
                base_url=settings.GERPGO_API_BASE_URL,
                # api_version=settings.GERPGO_API_VERSION
            )
            
            success, response = client.health_check()
            if not success:
                gerpgo_status = f'error: {response.get("error", "未知错误")}'
        except Exception as e:
            gerpgo_status = f'error: {str(e)}'
        
        status_data = {
            'status': 'running',
            'message': 'API服务正常运行',
            'timestamp': timezone.now(),
            'version': '1.0.0',
            'api_connections': {
                'database': db_status,
                'gerpgo_api': gerpgo_status
            }
        }
        
        serializer = StatusSerializer(data=status_data)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"API状态检查失败: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'API服务异常: {str(e)}',
            'timestamp': timezone.now()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 映射函数，从API获取的产品数据映射为统一格式
def map_product_data(product_data):
    """将Gerpgo产品数据映射到本地模型"""
    # 从用户提供的数据结构中提取所需字段
    return {
        'market_name': product_data.get('marketName'),
        'market_id': product_data.get('marketId'),
        'spu': product_data.get('spu'),
        'spu_name': product_data.get('spuName'),
        'sku': product_data.get('sellerSku'),
        'asin': product_data.get('asin'),
        'fnsku': product_data.get('fnsku'),
        'product_name': product_data.get('productName'),
        'category_name': product_data.get('categoryName'),
        'storage_type': product_data.get('storageType'),
        'storage_type_name': product_data.get('storageTypeName'),
        'fulfillment': product_data.get('fulfillment'),
        'sale_state' : product_data.get('state'),
        'sale_manager_name': product_data.get('sellingManagerName'),
        'product_manager_name':product_data.get('productManagerName'),
        'first_sale_date': product_data.get('firstSalesDate'),
        'package_length': product_data.get('packageL'),
        'package_width': product_data.get('packageW'),
        'package_height': product_data.get('packageH'),
        'package_weight': product_data.get('packageWeight'),
        'product_length': product_data.get('productL'),
        'product_width': product_data.get('productW'),
        'product_height': product_data.get('productH'),
        'product_weight': product_data.get('packageWeight'),
        'item_condition': '新品' if product_data.get('itemCondition') == '11' else '二手-类似新品' if product_data.get('itemCondition') == '1' else '二手',
        'status': 'active' if product_data.get('state') == 0 else 'inactive',
    }


# 同步产品数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_products_from_gerpgo(request):
    """从Gerpgo同步产品数据"""
    # 验证请求数据
    serializer = SyncRequestSerializer(data=request.data)
    if not serializer.is_valid(): # 验证请求数据是否有效
        logger.error(f"请求数据验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    force_full_sync = data.get('force_full_sync', False)
    page = data.get('page', 1)
    page_size = data.get('page_size', 100)
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='products',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步产品数据，批次ID: {sync_log.id}")
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步产品数据
        success_count = 0
        failed_count = 0
        has_more = True
        
        while has_more:
            logger.info(f"获取第{page}页产品数据，每页{page_size}条")
            # 获取产品列表
            success, response = client.get_products(page=page, page_size=page_size)
            
            if not success:
                error_msg = f"获取产品数据失败: {response.get('error', '未知错误')}"
                logger.error(error_msg)
                failed_count += 1
                break
            
            logger.info(f"成功获取API响应，响应数据类型: {type(response)}, 是否包含data字段: {'data' in response}")
            # 记录响应结构摘要
            if isinstance(response, dict):
                logger.info(f"响应字典键: {list(response.keys())}")
                if 'data' in response:
                    data_content = response['data']
                    logger.info(f"data字段类型: {type(data_content)}")
                    if isinstance(data_content, dict):
                        logger.info(f"data字典键: {list(data_content.keys())}")
                        
            # 处理产品数据 - 适配新的API响应格式
            products_data = []
            if isinstance(response, dict):
                data = response.get('data', {})
                # 根据实际接口返回的数据结构调整
                if isinstance(data, dict):
                    products_data = data.get('rows', [])
                    logger.info(f"从data.rows获取产品列表，数量: {len(products_data)}")
                elif isinstance(data, list):
                    products_data = data
                    logger.info(f"从data直接获取产品列表，数量: {len(products_data)}")
            
            if not products_data:
                logger.warning(f"未获取到产品数据，停止同步")
                has_more = False
                break
            
            # 记录前3个产品数据的结构，用于调试
            if len(products_data) > 0:
                sample_product = products_data[0]
                logger.info(f"样本产品数据键: {list(sample_product.keys())}")
                logger.info(f"样本产品SKU: {sample_product.get('sellerSku')}, 渠道: {sample_product.get('marketName')}")
            
            sync_log.total_count += len(products_data)
            
            for idx, product_data in enumerate(products_data):
                try:
                    # 转换数据格式
                    product_data_mapped = map_product_data(product_data)
                    logger.debug(f"映射后产品数据{idx+1}/{len(products_data)}: SKU={product_data_mapped.get('sku')}, 价格={product_data_mapped.get('price')}")
                    
                    # 检查必要字段是否存在
                    if not product_data_mapped.get('sku'):
                        logger.error(f"产品数据缺少SKU字段: {product_data}")
                        failed_count += 1
                        continue
                    
                    if not product_data_mapped.get('asin'):
                        logger.warning(f"产品数据缺少ASIN字段: SKU={product_data_mapped.get('sku')}")
                    
                    # 更新或创建产品
                    logger.debug(f"准备保存产品: {product_data_mapped.get('sku')}")
                    product, created = Product.objects.update_or_create(
                        market_name=product_data_mapped.get('market_name'),
                        sku=product_data_mapped.get('sku'),
                        asin=product_data_mapped.get('asin'),
                        fnsku=product_data_mapped.get('fnsku'),
                        item_condition=product_data_mapped.get('item_condition'),
                        sale_state=product_data_mapped.get('sale_state'),
                        defaults=product_data_mapped
                    )
                    
                    # 验证数据是否真的保存成功
                    saved_product = Product.objects.filter(sku=product_data_mapped['sku']).first()
                    if saved_product:
                        success_count += 1
                        logger.info(f"{'创建' if created else '更新'}产品成功: {saved_product.asin} (SKU: {saved_product.sku}), ID: {saved_product.id}")
                    else:
                        logger.error(f"产品保存失败，数据库中未找到: {product_data_mapped.get('sku')}")
                        failed_count += 1
                    
                except Exception as e:
                    logger.error(f"处理产品数据失败: {str(e)}")
                    logger.error(f"失败的产品数据: {product_data}")
                    failed_count += 1
            
            # 检查是否还有更多数据 - 使用新的数据结构字段
            total = response.get('data', {}).get('total', 0)
            current_page = response.get('data', {}).get('page', 1)
            page_size = response.get('data', {}).get('size', page_size)
            total_pages = (total + page_size - 1) // page_size
            has_more = current_page < total_pages
            page = current_page + 1
            logger.info(f"当前同步进度: 第{current_page}/{total_pages}页，已处理{sync_log.total_count}条数据")
        
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        sync_log.end_time = timezone.now()
        sync_log.save()
        logger.info(f"产品同步完成，批次ID: {sync_log.id}，成功 {success_count} 条，失败 {failed_count} 条")
        
        return Response({
            'status': 'success',
            'message': f'产品同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"产品同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'产品同步失败: {str(e)}',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 前端数据接口，用于前端获取产品列表数据，支持分页、搜索和仓库筛选
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def get_products_data(request):
    """获取产品列表数据"""
    try:
        # 获取查询参数
        search = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 10))
        
        # 构建查询
        queryset = Product.objects.all()
        
        # 搜索过滤
        if search:
            queryset = queryset.filter(
                name__icontains=search
            ) | queryset.filter(
                sku__icontains=search
            )
        
        # 分页
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        products = list(queryset[start:end].values(
            'id', 'sku', 'price', 'cost', 'status'
        ))
        
        return Response({
            'success': True,
            'data': {
                'products': products,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f'获取产品列表数据失败: {str(e)}')
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 辅助函数 - 映射FBA库存数据
def map_fba_inventory_data(inventory_data):
    """将Gerpgo FBA库存数据映射为统一格式"""
    
    # 辅助函数：将空字符串或None转换为默认值
    def safe_decimal(value, default=None):
        """安全转换为Decimal类型，空字符串或空值返回None或默认值"""
        if value == '' or value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(value, default=0):
        """安全转换为整数类型，空字符串或空值返回默认值"""
        if value == '' or value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def safe_str(value, default=''):
        """安全转换为字符串类型，None返回空字符串"""
        if value is None or value == '':
            return default
        return str(value)
    
    # 从用户提供的数据结构中提取所需字段
    return {
        'snapshot_date': inventory_data.get('snapshotDate'),
        'sku': inventory_data.get('sku'),
        'fnsku': inventory_data.get('fnsku'),
        'asin': inventory_data.get('asin'),
        'product_name': inventory_data.get('productName'),
        'condition': inventory_data.get('condition'),
        'available_quantity': safe_int(inventory_data.get('avaliableQuantity'), 0),
        'qty_with_removals_in_progress': safe_int(inventory_data.get('qtyWithRemovalsInProgress'), 0),
        'inv_age_0_to_90_days': safe_int(inventory_data.get('invAge0To90Days'), 0),
        'inv_age_91_to_180_days': safe_int(inventory_data.get('invAge91To180Days'), 0),
        'inv_age_181_to_270_days': safe_int(inventory_data.get('invAge181To270Days'), 0),
        'inv_age_271_to_365_days': safe_int(inventory_data.get('invAge271To365Days'), 0),
        'inv_age_365_plus_days': safe_int(inventory_data.get('invAge365PlusDays'), 0),
        'qty_to_be_charged_ltsf6mo': safe_int(inventory_data.get('qtyToBeChargedLtsf6mo'), 0),
        'qty_predicted_to_be_charged_ltsf6mo': safe_decimal(inventory_data.get('projectedLtsf6Mo'), None),
        'qty_to_be_charged_ltsf12mo': safe_int(inventory_data.get('qtyToBeChargedLtsf12mo'), 0),
        'qty_predicted_to_be_charged_ltsf12mo': safe_decimal(inventory_data.get('projectedLtsf12Mo'), None),
        'units_shipped_last_7_days': safe_int(inventory_data.get('unitsShippedLast7Days'), 0),
        'units_shipped_last_30_days': safe_int(inventory_data.get('unitsShippedLast30Days'), 0),
        'units_shipped_last_60_days': safe_int(inventory_data.get('unitsShippedLast60Days'), 0),
        'units_shipped_last_90_days': safe_int(inventory_data.get('unitsShippedLast90Days'), 0),
        'alert': safe_str(inventory_data.get('alert')),
        'your_price': safe_str(inventory_data.get('yourPrice')),
        'sales_price': safe_str(inventory_data.get('salesPrice')),
        'lowest_price_new': safe_str(inventory_data.get('lowestPriceNew')),
        'lowest_price_used': safe_str(inventory_data.get('lowestPriceUsed')),
        'recommended_action': inventory_data.get('recommendedAction'),
        'healthy_inventory_level': safe_int(inventory_data.get('healthyInventoryLevel'), None),
        'recommended_sales_price': safe_str(inventory_data.get('recommendedSalesPrice')),
        'recommended_sale_duration': safe_str(inventory_data.get('recommendedSaleDuration')),
        'recommended_removal_qty': safe_str(inventory_data.get('recommendedRemovalQty')),
        'removal_cost_savings': safe_str(inventory_data.get('estimatedCostSavingsOfRemoval')),
        'sell_through': inventory_data.get('sellThrough'),
        'item_volume': safe_str(inventory_data.get('itemVolume')),
        'cubic_feet': safe_str(inventory_data.get('cubicFeet')),
        'storage_type': inventory_data.get('storageType'),
        'market_place': inventory_data.get('marketplace'),
        'estimated_storage_cost': safe_str(inventory_data.get('estimatedStorageCost')),
        'create_date': inventory_data.get('createDate'),
        'update_date': inventory_data.get('updateDate'),
        'warehouse_id': safe_int(inventory_data.get('warehouseId'), 0),
        'warehouse_name': inventory_data.get('warehouseName'),
        'inv_age_0_to_30_days': safe_int(inventory_data.get('invAge0To30Days'), 0),
        'inv_age_31_to_60_days': safe_int(inventory_data.get('invAge31To60Days'), 0),
        'inv_age_61_to_90_days': safe_int(inventory_data.get('invAge61To90Days'), 0),
        'inv_age_271_to_330_days': safe_int(inventory_data.get('invAge271To330Days'), 0),
        'inv_age_331_to_365_days': safe_int(inventory_data.get('invAge331To365Days'), 0),
    }

# 同步FBA库存数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_fba_inventory_from_gerpgo(request):
    """从Gerpgo同步FBA库存数据"""
    # 验证请求数据
    serializer = SyncRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"请求数据验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    force_full_sync = data.get('force_full_sync', False)
    page = data.get('page', 1)
    page_size = data.get('page_size', 100)
    warehouse_ids = data.get('warehouse_ids', None)
    
    # 获取日期参数
    begin_date = data.get('start_date', None)
    end_date = data.get('end_date', None)

    # 如果没有传入日期参数，默认为近3天
    if not begin_date or not end_date:
        end_date = datetime.now().date()
        begin_date = end_date - timedelta(days=3)
        logger.info(f"未提供日期范围，使用默认值：开始日期={begin_date}, 结束日期={end_date}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='inventory',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步FBA库存数据，批次ID: {sync_log.id}")
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步库存数据
        success_count = 0
        failed_count = 0
        has_more = True
        
        while has_more:
            logger.info(f"获取第{page}页FBA库存数据，每页{page_size}条")
            # 获取库存列表
            params = {
                'page': page,
                'pageSize': page_size
            }
            if warehouse_ids:
                params['warehouseIds'] = warehouse_ids
            
            # 添加日期参数到请求中
            if begin_date:
                params['beginDate'] = begin_date.strftime('%Y-%m-%d')
            if end_date:
                params['endDate'] = end_date.strftime('%Y-%m-%d')
            
            success, response = client.get_fba_inventory(**params)
            
            if not success:
                error_msg = f"获取FBA库存数据失败: {response.get('error', '未知错误')}"
                logger.error(error_msg)
                failed_count += 1
                break
            
            # 处理库存数据
            inventory_data = []
            if isinstance(response, dict) and 'data' in response:
                data = response['data']
                if isinstance(data, dict):
                    inventory_data = data.get('rows', [])
                    logger.info(f"从data.rows获取库存列表，数量: {len(inventory_data)}")
            
            if not inventory_data:
                logger.warning(f"未获取到库存数据，停止同步")
                has_more = False
                break
            
            # 记录前3个库存数据的结构，用于调试
            if len(inventory_data) > 0:
                sample_inventory = inventory_data[0]
                logger.info(f"样本库存数据键: {list(sample_inventory.keys())}")
                logger.info(f"样本库存SKU: {sample_inventory.get('sku')}, 数量: {sample_inventory.get('avaliableQuantity')}")
            
            sync_log.total_count += len(inventory_data)
            
            for idx, item_data in enumerate(inventory_data):
                try:
                    # 转换数据格式
                    inventory_data_mapped = map_fba_inventory_data(item_data)
                    logger.debug(f"映射后库存数据{idx+1}/{len(inventory_data)}: SKU={inventory_data_mapped.get('sku')}, 数量={inventory_data_mapped.get('available_quantity')}")
                    
                    # 检查必要字段是否存在
                    if not inventory_data_mapped.get('sku'):
                        logger.error(f"库存数据缺少SKU字段: {item_data}")
                        failed_count += 1
                        continue
                    
                    # 创建或更新库存记录
                    try:
                        # 使用update_or_create保存数据
                        inventory, created = Inventory.objects.update_or_create(
                            snapshot_date=inventory_data_mapped.get('snapshot_date'),
                            warehouse_name=inventory_data_mapped.get('warehouse_name'),
                            fnsku=inventory_data_mapped.get('fnsku'),
                            condition=inventory_data_mapped.get('condition'),
                            sku=inventory_data_mapped.get('sku'),
                            asin=inventory_data_mapped.get('asin'),
                            market_place=inventory_data_mapped.get('market_place'),
                            defaults=inventory_data_mapped
                        )
                        
                        inventory.save()
                        success_count += 1
                        logger.info(f"处理库存数据成功: SKU={inventory_data_mapped.get('sku')}, 数量={inventory_data_mapped.get('available_quantity')}")
                        
                    except Exception as db_error:
                        logger.error(f"数据库保存失败: {str(db_error)}")
                        logger.error(f"失败的库存数据: {inventory_data_mapped}")
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"处理库存数据时发生异常: {str(e)}")
                    failed_count += 1
            
            # 检查是否还有更多数据
            total = response.get('data', {}).get('total', 0)
            current_page = response.get('data', {}).get('page', 1)
            page_size = response.get('data', {}).get('size', page_size)
            total_pages = (total + page_size - 1) // page_size
            has_more = current_page < total_pages
            page = current_page + 1
            logger.info(f"当前同步进度: 第{current_page}/{total_pages}页，已处理{sync_log.total_count}条数据")
        
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        sync_log.end_time = timezone.now()
        sync_log.save()
        logger.info(f"FBA库存同步完成，批次ID: {sync_log.id}，成功 {success_count} 条，失败 {failed_count} 条")
        
        return Response({
            'status': 'success',
            'message': f'FBA库存同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"FBA库存同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'FBA库存同步失败: {str(e)}',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 前端数据接口 - FBA库存列表数据
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def get_fba_inventory_data(request):
    """获取FBA库存列表数据"""
    try:
        # 获取查询参数
        search = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 10))
        warehouse_id = request.query_params.get('warehouseId', None)
        
        # 尝试从本地数据库获取数据
        inventory_query = Inventory.objects.all()
        
        # 应用搜索条件
        if search:
            inventory_query = inventory_query.filter(
                Q(sku__icontains=search) | 
                Q(product_name__icontains=search)
            )
            
        # 应用仓库筛选
        if warehouse_id:
            # 处理warehouse_id可能是字符串的情况
            try:
                warehouse_id_int = int(warehouse_id)
                inventory_query = inventory_query.filter(warehouse_id=warehouse_id_int)
            except ValueError:
                logger.warning(f"无效的仓库ID: {warehouse_id}")
                
        # 计算总数和分页
        total = inventory_query.count()
        inventory_data = inventory_query.order_by('-updated_at')[ 
            (page-1)*page_size : page*page_size
        ]
        
        # 如果数据库有数据，返回数据库的数据
        if inventory_data.exists():
            # 格式化数据
            formatted_data = []
            for item in inventory_data:
                formatted_item = {
                    'id': item.gerpgo_id,
                    'sku': item.sku,
                    'productName': item.product_name,
                    'avaliableQuantity': item.available_quantity,
                    'warehouseId': item.warehouse_id,
                    'warehouseName': item.warehouse_name,
                    'storageType': item.storage_type,
                    'salesPrice': float(item.sales_price) if item.sales_price else 0,
                    'currency': item.currency,
                    'condition': item.condition,
                    'invAge0To30Days': item.inv_age_0_to_30_days,
                    'invAge31To60Days': item.inv_age_31_to_60_days,
                    'invAge61To90Days': item.inv_age_61_to_90_days,
                    'invAge91To180Days': item.inv_age_91_to_180_days,
                    'invAge181To270Days': item.inv_age_181_to_270_days,
                    'invAge271To365Days': item.inv_age_271_to_365_days,
                    'invAge365PlusDays': item.inv_age_365_plus_days,
                    'unitsShippedLast7Days': item.units_shipped_last_7_days,
                    'unitsShippedLast30Days': item.units_shipped_last_30_days,
                    'unitsShippedLast60Days': item.units_shipped_last_60_days,
                    'unitsShippedLast90Days': item.units_shipped_last_90_days,
                    'sellThrough': item.sell_through,
                    'healthyInventoryLevel': item.healthy_inventory_level,
                    'updateDate': item.updated_at.strftime('%Y-%m-%d') if item.updated_at else ''
                }
                formatted_data.append(formatted_item)
            
            return Response({
                'success': True,
                'data': {
                    'inventory': formatted_data,
                    'total': total,
                    'page': page,
                    'pageSize': page_size
                }
            })
        else:
            # 如果数据库没有数据，从API获取数据
            client = GerpgoAPIClient(
                appId=settings.GERPGO_APP_ID,
                appKey=settings.GERPGO_APP_KEY,
                base_url=settings.GERPGO_API_BASE_URL
            )
            
            params = {
                'page': page,
                'pageSize': page_size
            }
            if warehouse_id:
                params['warehouseId'] = warehouse_id
            if search:
                params['search'] = search
            
            success, response = client.get_fba_inventory(**params)
            
            if not success:
                return Response({
                    'success': False,
                    'error': response.get('error', '获取FBA库存数据失败')
                }, status=500)
            
            return Response({
                'success': True,
                'data': response
            })
            
    except Exception as e:
        logger.error(f"获取FBA库存数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 同步店铺市场信息
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_marketplaces_from_gerpgo(request):
    """从Gerpgo同步店铺市场信息"""
    # 验证请求数据
    serializer = SyncRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"请求数据验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    force_full_sync = data.get('force_full_sync', False)
    page = data.get('page', 1)
    page_size = data.get('page_size', 100)
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='marketplaces',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步店铺市场信息，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步市场信息数据
        success_count = 0
        failed_count = 0
        has_more = True
        
        # 添加辅助函数用于安全的类型转换
        def safe_int_convert(value, default=0):
            """安全地将值转换为整数"""
            if value is None:
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                logger.warning(f"无法转换为整数: {value}")
                return default
                
        def safe_datetime_convert(value):
            """安全地将值转换为日期时间"""
            if value is None:
                return None
            try:
                # 尝试解析字符串格式的日期时间
                if isinstance(value, str):
                    # 处理不同格式的日期时间字符串
                    formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']
                    for fmt in formats:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                    logger.warning(f"无法解析日期时间字符串: {value}")
                    return None
                elif isinstance(value, datetime):
                    return value
            except Exception as e:
                logger.warning(f"日期时间转换异常: {str(e)}")
            return None
            
        def safe_json_convert(value):
            """安全地将值转换为JSON"""
            if value is None:
                return None
            try:
                if isinstance(value, str):
                    # 如果是字符串，尝试解析为JSON
                    return json.loads(value)
                elif isinstance(value, (dict, list)):
                    # 如果已经是字典或列表，直接返回
                    return value
                else:
                    # 其他类型，转换为字符串后尝试解析
                    return json.loads(str(value))
            except (ValueError, TypeError) as e:
                logger.warning(f"JSON转换异常: {str(e)}, 值: {value}")
                return None
        
        while has_more:
            logger.info(f"获取第{page}页市场信息数据，每页{page_size}条")
            # 获取市场列表
            params = {
                'page': page,
                'pageSize': page_size
            }
            
            success, response = client.get_marketplaces(**params)
            
            if not success:
                error_msg = f"获取市场信息数据失败: {response.get('error', '未知错误')}"
                logger.error(error_msg)
                detailed_errors.append(error_msg)
                failed_count += 1
                break
            
            # 处理市场数据 - 修正数据结构解析逻辑
            market_data = []
            if isinstance(response, dict) and 'data' in response:
                data = response['data']
                if isinstance(data, dict) and 'rows' in data:
                    rows = data.get('rows', [])
                    logger.info(f"从data.rows获取区域数据，数量: {len(rows)}")
                    
                    # 遍历每个区域数据，提取其中的marketListVos
                    for row in rows:
                        if isinstance(row, dict) and 'marketListVos' in row:
                            market_list_vos = row.get('marketListVos', [])
                            market_data.extend(market_list_vos)
                            logger.info(f"从marketListVos提取市场数据，数量: {len(market_list_vos)}")
            
            if not market_data:
                logger.warning(f"未获取到市场数据，停止同步")
                has_more = False
                break
            
            # 记录前3个市场数据的结构，用于调试
            if len(market_data) > 0:
                sample_market = market_data[0]
                logger.info(f"样本市场数据键: {list(sample_market.keys())}")
                logger.info(f"样本市场名称: {sample_market.get('marketName')}, ID: {sample_market.get('marketId')}")
            
            sync_log.total_count += len(market_data)
            
            for idx, item_data in enumerate(market_data):
                try:
                    marketplaces_data_mapped = map_market_data(item_data)
                    logger.debug(f"映射后市场数据{idx+1}/{len(market_data)}: 名称={marketplaces_data_mapped.get('market_name')}, ID={marketplaces_data_mapped.get('market_id')}")
                    
                    # 检查必要字段是否存在
                    if not marketplaces_data_mapped.get('market_id'):
                        error_msg = f"市场数据缺少market_id字段: {item_data}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                    
                    # 创建或更新市场记录
                    try:
                        # 使用update_or_create保存数据
                        market, created = Market.objects.update_or_create(
                            market_id=marketplaces_data_mapped.get('market_id'), # 主键
                            defaults={
                                **marketplaces_data_mapped,
                                'last_sync_time': timezone.now(),
                                'sync_status': 'success'
                            }
                        )
                        
                        market.save()
                        success_count += 1
                        logger.info(f"处理市场数据成功: 名称={marketplaces_data_mapped.get('market_name')}, ID={marketplaces_data_mapped.get('market_id')}")
                        
                        # 同时创建或更新卖家市场关联记录
                        if marketplaces_data_mapped.get('seller_id') and marketplaces_data_mapped.get('area_id'):
                            try:
                                seller_marketplace, sm_created = SellerMarketplace.objects.update_or_create(
                                    seller_id=marketplaces_data_mapped.get('seller_id'),
                                    area_id=marketplaces_data_mapped.get('area_id'), 
                                    defaults={
                                        'area_name': marketplaces_data_mapped.get('area_name'),
                                        'last_sync_time': timezone.now(),
                                        'sync_status': 'success'
                                    }
                                )
                                seller_marketplace.save()
                                logger.debug(f"{'创建' if sm_created else '更新'}卖家市场关联成功: SellerID={marketplaces_data_mapped.get('seller_id')}, AreaID={marketplaces_data_mapped.get('area_id')}")
                            except Exception as sm_error:
                                error_msg = f"创建卖家市场关联失败: {str(sm_error)}, SellerID={marketplaces_data_mapped.get('seller_id')}, AreaID={marketplaces_data_mapped.get('area_id')}"
                                logger.error(error_msg)
                                detailed_errors.append(error_msg)
                                # 注意：这里不增加failed_count，因为主市场数据已成功保存
                        
                    except Exception as db_error:
                        error_msg = f"数据库保存失败: {str(db_error)}, 数据: {marketplaces_data_mapped}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        
                except Exception as e:
                    error_msg = f"处理市场数据时发生异常: {str(e)}, 索引: {idx}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
            
            # 检查是否还有更多数据
            total = response.get('data', {}).get('total', 0)
            current_page = response.get('data', {}).get('page', 1)
            page_size = response.get('data', {}).get('size', page_size)
            total_pages = (total + page_size - 1) // page_size
            has_more = current_page < total_pages
            page = current_page + 1
            logger.info(f"当前同步进度: 第{current_page}/{total_pages}页，已处理{sync_log.total_count}条数据")
        
        # 更新同步日志
        sync_log.status = 'success' if failed_count == 0 else 'partial_success'
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        # 保存详细错误信息，但限制长度
        if detailed_errors:
            # 只保存前5个错误详情，避免字段过长
            sync_log.error_message = '\n'.join(detailed_errors[:5]) + (f"\n... 还有{len(detailed_errors)-5}个错误" if len(detailed_errors) > 5 else '')
        sync_log.end_time = timezone.now()
        sync_log.save()
        logger.info(f"店铺市场信息同步完成，批次ID: {sync_log.id}，成功 {success_count} 条，失败 {failed_count} 条")
        
        return Response({
            'status': 'success',
            'message': f'店铺市场信息同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"店铺市场信息同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.error_message += '\n详细错误: ' + '\n'.join(detailed_errors[:5])
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'店铺市场信息同步失败: {str(e)}',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 前端数据接口 - 市场列表数据
@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def get_marketplaces_data(request):
    """获取市场列表数据"""
    try:
        # 获取查询参数
        search = request.query_params.get('search', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 10))
        
        # 尝试从本地数据库获取数据
        market_query = Market.objects.all()
        
        # 应用搜索条件
        if search:
            market_query = market_query.filter(
                Q(market_name__icontains=search) | 
                Q(seller_id__icontains=search) |
                Q(market__icontains=search)
            )
            
        # 计算总数和分页
        total = market_query.count()
        market_data = market_query.order_by('-updated_at')[ 
            (page-1)*page_size : page*page_size
        ]
        
        # 如果数据库有数据，返回数据库的数据
        if market_data.exists():
            # 格式化数据
            formatted_data = []
            for item in market_data:
                formatted_item = {
                    'id': item.gerpgo_id,
                    'marketId': item.market_id,
                    'market': item.market,
                    'marketName': item.market_name,
                    'areaId': item.area_id,
                    'areaName': item.area_name,
                    'sellerId': item.seller_id,
                    'store': item.store,
                    'account': item.account,
                    'syncStatus': item.sync_status,
                    'lastSyncTime': item.last_sync_time.strftime('%Y-%m-%d %H:%M:%S') if item.last_sync_time else '',
                    'updatedAt': item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                formatted_data.append(formatted_item)
            
            return Response({
                'success': True,
                'data': {
                    'marketplaces': formatted_data,
                    'total': total,
                    'page': page,
                    'pageSize': page_size
                }
            })
        else:
            # 如果数据库没有数据，从API获取数据
            client = GerpgoAPIClient(
                appId=settings.GERPGO_APP_ID,
                appKey=settings.GERPGO_APP_KEY,
                base_url=settings.GERPGO_API_BASE_URL
            )
            
            params = {
                'page': page,
                'pageSize': page_size
            }
            if search:
                params['search'] = search
            
            success, response = client.get_marketplaces(**params)
            
            if not success:
                return Response({
                    'success': False,
                    'error': response.get('error', '获取市场信息数据失败')
                }, status=500)
            
            return Response({
                'success': True,
                'data': response
            })
            
    except Exception as e:
        logger.error(f"获取市场信息数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


def map_market_data(market_data):
    """将Gerpgo市场数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段
    return {
        'area_id': market_data.get('areaId'),
        'area_name': market_data.get('areaName'),
        'seller_id': market_data.get('sellerId'),
        'market': market_data.get('market'),
        'market_id': market_data.get('marketId'),
        'market_name': market_data.get('marketName'),
        'store': market_data.get('store'),
        'country_id': market_data.get('countryId', 0),
        'country_code': market_data.get('countryCode'),
        'country_name': market_data.get('countryName'),
        'account': market_data.get('account'),
        'ads_state': market_data.get('adsState'),
        'api_state': market_data.get('apiState'),
        'state': market_data.get('state', 0),
        'disable_sub_account': market_data.get('disableSubAccount', 0),
        'record_date': market_data.get('recordDate')
    }


# 映射SP广告产品数据
def map_sp_ad_data(ad_data):
    """将Gerpgo返回的SP广告产品数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
            'market_id': ad_data.get('marketId'),
            'portfolio_id': ad_data.get('portfolioId'),
            'portfolio_name': ad_data.get('portfolioName'),
            'campaign_id': ad_data.get('campaignId'),
            'campaign_name': ad_data.get('campaignName'),
            'group_id': ad_data.get('groupId'),
            'group_name': ad_data.get('groupName'),
            'ad_id': ad_data.get('adId'),
            'group_targeting_type': ad_data.get('groupTargetingType'),
            'msku': ad_data.get('msku'),
            'asin': ad_data.get('asin'),
            'state': ad_data.get('state', 0), 
            'serving_status': ad_data.get('servingStatus'),
            'create_date': ad_data.get('createDate'),
            'impressions': ad_data.get('impressions'),
            'clicks': ad_data.get('clicks'),
            'cost': ad_data.get('cost'),
            'ads_orders': ad_data.get('adsOrders'),
            'ads_sales': ad_data.get('adsSales'),
            'ads_product_orders': ad_data.get('adsProductOrders'),
            'ads_product_sales': ad_data.get('adsProductSales'),
            'other_product_sales': ad_data.get('otherProductSales'),
    }


# 同步SP广告产品数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sp_ad_data_from_gerpgo(request):
    """从Gerpgo同步SP广告产品数据"""
    # 验证请求数据
    serializer = SPADDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SPAD数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    # 获取日期参数，同时支持两种命名方式
    start_date = data.get('start_date') or data.get('startDataDate')
    end_date = data.get('end_date') or data.get('endDataDate')
    
    # 如果没有提供日期范围，设置默认值为最近7天
    if not start_date or not end_date:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        logger.info(f"未提供日期范围，使用默认值：开始日期={start_date}, 结束日期={end_date}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sp_ad_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SP广告产品数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SPAD数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SP广告产品数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 分页获取所有数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的第 {page_num} 页数据")
                
                # 构建请求参数
                params = {
                    'marketId': market_id,
                    'count': count
                }
                
                # 添加nextId参数
                if next_id is not None:
                    params['nextId'] = next_id
                    logger.debug(f"当前分页参数 - nextId: {next_id}")
                
                if start_date:
                    params['startDataDate'] = start_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置开始日期: {params['startDataDate']}")
                if end_date:
                    params['endDataDate'] = end_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置结束日期: {params['endDataDate']}")
                
                # 调用API获取数据
                success, response = client.get_sp_ad(**params)
                
                # 增加延迟，确保符合每1秒1次的限流规则
                import time
                time.sleep(1.1)  # 增加1.1秒延迟，确保不超过限流
                
                if not success:
                    error_msg = f"获取市场 {market_id} 的SP广告产品数据失败: {response.get('error', '未知错误')}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    
                    # 检查是否为限流错误（509）
                    if '接口调用次数已超过限制次数' in str(response.get('error', '')):
                        logger.warning(f"触发限流，等待2秒后重试该页面...")
                        time.sleep(2)  # 遇到限流时额外等待
                        # 重新尝试该页面
                        continue
                    
                    break  # 暂停该市场的同步，继续下一个市场
                
                # 处理返回的数据
                ad_data_list = response.get('data', [])
                if not ad_data_list:
                    logger.warning(f"市场 {market_id} 第 {page_num} 页未获取到SP广告产品数据")
                else:
                    sync_log.total_count += len(ad_data_list)
                    total_processed_for_market += len(ad_data_list)
                    logger.info(f"成功获取市场ID {market_id} 第 {page_num} 页数据，共 {len(ad_data_list)} 条，累计处理 {total_processed_for_market} 条")
                
                # 处理每条广告数据
                for idx, ad_data in enumerate(ad_data_list):
                    try:
                        # 映射API返回的数据到模型字段
                        ad_product_data = {
                            **map_sp_ad_data(ad_data),                          
                        }
                        
                        # 处理日期字段
                        if 'createDate' in ad_data:
                            try:
                                ad_product_data['create_date'] = datetime.strptime(ad_data['createDate'], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                logger.warning(f"无法解析createDate: {ad_data.get('createDate')}")
                        
                        if 'reportDate' in ad_data:
                            try:
                                ad_product_data['create_date'] = datetime.strptime(ad_data['createDate'], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                logger.warning(f"无法解析createDate: {ad_data.get('createDate')}")
                        
                        # 检查必要字段
                        if not ad_product_data.get('ad_id'):
                            error_msg = f"广告数据缺少ad_id字段: {ad_data}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            failed_count += 1
                            continue
                        
                        if not ad_product_data.get('create_date'):
                            ad_product_data['create_date'] = timezone.now().date()
                        
                        # 创建或更新广告产品记录
                        try:
                            ads_product, created = AdsSpProduct.objects.update_or_create(
                                # portfolio_id=ad_product_data.get('portfolio_id'),
                                campaign_id=ad_product_data.get('campaign_id'),
                                group_id=ad_product_data.get('group_id'),
                                ad_id=ad_product_data.get('ad_id'),
                                msku=ad_product_data.get('msku'),
                                asin=ad_product_data.get('asin'),
                                create_date=ad_product_data.get('create_date'),
                                defaults=ad_product_data
                                
                            )
                            
                            ads_product.save()
                            success_count += 1
                            logger.debug(f"处理广告产品数据成功: MSKU={ad_product_data.get('msku')}, ASIN={ad_product_data.get('asin')}")
                            
                        except Exception as db_error:
                            error_msg = f"数据库保存失败: {str(db_error)}, 数据: {ad_product_data}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            failed_count += 1
                            
                    except Exception as e:
                        error_msg = f"处理广告产品数据时发生异常: {str(e)}, 索引: {idx}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                
                # 更新分页参数
                next_id = response.get('next_id')
                has_more = response.get('has_more', False)
                logger.debug(f"更新分页参数 - next_id: {next_id}, has_more: {has_more}")
                page_num += 1
        
        # 更新同步日志
        sync_log.status = 'success' if failed_count == 0 else 'partial_success'
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        # 保存详细错误信息，但限制长度
        if detailed_errors:
            # 只保存前5个错误详情，避免字段过长
            sync_log.error_message = '\n'.join(detailed_errors[:5]) + (f"\n... 还有{len(detailed_errors)-5}个错误" if len(detailed_errors) > 5 else '')
        sync_log.end_time = timezone.now()
        sync_log.save()
        logger.info(f"SP广告产品数据同步完成，批次ID: {sync_log.id}，成功 {success_count} 条，失败 {failed_count} 条")
        
        return Response({
            'status': 'success',
            'message': f'SP广告产品数据同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SP广告产品数据同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.error_message += '\n详细错误: ' + '\n'.join(detailed_errors[:5])
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'SP广告产品数据同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_sp_ad_data(request):
    """获取SP广告产品数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        msku = request.GET.get('msku')
        asin = request.GET.get('asin')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        campaign_id = request.GET.get('campaignId')
        
        # 构建查询
        queryset = AdsSpProduct.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if msku:
            queryset = queryset.filter(msku__icontains=msku)
        if asin:
            queryset = queryset.filter(asin=asin)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        
        # 按报告日期和市场ID排序
        queryset = queryset.order_by('-report_date', 'market_id')
        
        # 分页
        total = queryset.count()
        paginator = Paginator(queryset, page_size)
        paginated_queryset = paginator.get_page(page)
        
        # 格式化数据
        formatted_data = []
        for item in paginated_queryset:
            formatted_item = {
                'id': item.id,
                'marketId': item.market_id,
                'msku': item.msku,
                'asin': item.asin,
                'listingTitle': item.listing_title,
                'campaignId': item.campaign_id,
                'campaignName': item.campaign_name,
                'groupId': item.group_id,
                'groupName': item.group_name,
                'adId': item.ad_id,
                'impressions': item.impressions,
                'clicks': item.clicks,
                'cost': float(item.cost),
                'adsSales': float(item.ads_sales),
                'adsOrders': item.ads_orders,
                'ctr': item.ctr,
                'cpc': item.cpc,
                'acos': item.acos,
                'roas': item.roas,
                'reportDate': item.report_date.strftime('%Y-%m-%d'),
                'createDate': item.create_date.strftime('%Y-%m-%d') if item.create_date else None,
                'servingStatus': item.serving_status
            }
            formatted_data.append(formatted_item)
        
        return Response({
            'success': True,
            'data': {
                'spAdData': formatted_data,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
        
    except Exception as e:
        logger.error(f"获取SP广告产品数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 映射SP广告关键词数据
def map_sp_kw_data(keyword_data):
    """将Gerpgo返回的SP广告关键词数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': keyword_data.get('marketId'),
        'portfolio_id': keyword_data.get('portfolioId'),
        'portfolio_name': keyword_data.get('portfolioName'),
        'campaign_id': keyword_data.get('campaignId'),
        'campaign_name': keyword_data.get('campaignName'),
        'group_id': keyword_data.get('groupId'),
        'group_name': keyword_data.get('groupName'),
        'keyword_id': keyword_data.get('keywordId'),
        'keyword_text': keyword_data.get('keywordText'),
        'match_type': keyword_data.get('matchType'),
        'bid': keyword_data.get('bid'),
        'serving_status': keyword_data.get('servingStatus'),
        'create_date': keyword_data.get('createDate'),
        'impressions': keyword_data.get('impressions'),
        'clicks': keyword_data.get('clicks'),
        'cost': keyword_data.get('cost'),
        'ads_orders': keyword_data.get('adsOrders'),
        'ads_sales': keyword_data.get('adsSales'),
        'ads_product_orders': keyword_data.get('adsProductOrders'),
        'ads_product_sales': keyword_data.get('adsProductSales'),
        'other_product_sales': keyword_data.get('otherProductSales'),
    }


# 同步SP广告关键词数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sp_kw_data_from_gerpgo(request):
    """从Gerpgo同步SP广告关键词数据"""
    # 验证请求数据
    serializer = SPKWDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SPKW数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    # 获取日期参数，同时支持两种命名方式
    start_date = data.get('start_date') or data.get('startDataDate')
    end_date = data.get('end_date') or data.get('endDataDate')
    
    # 如果没有日期参数，默认使用近7天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        logger.info(f"未提供日期参数，默认使用近7天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")

    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sp_kw_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SP广告关键词数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SPKW数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SP广告关键词数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 分页获取所有数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的第 {page_num} 页数据")
                
                # 构建请求参数
                params = {
                    'marketId': market_id,
                    'count': count
                }
                
                # 添加nextId参数
                if next_id is not None:
                    params['nextId'] = next_id
                    logger.debug(f"当前分页参数 - nextId: {next_id}")
                
                if start_date:
                    params['startDataDate'] = start_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置开始日期: {params['startDataDate']}")
                if end_date:
                    params['endDataDate'] = end_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置结束日期: {params['endDataDate']}")
                
                # 调用API获取数据
                success, response = client.get_sp_kw(**params)
                
                # 增加延迟，确保符合每1秒1次的限流规则
                import time
                time.sleep(1.1)  # 增加1.1秒延迟，确保不超过限流
                
                if not success:
                    error_msg = f"获取市场 {market_id} 的SP广告关键词数据失败: {response.get('error', '未知错误')}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    
                    # 检查是否为限流错误（509）
                    if '接口调用次数已超过限制次数' in str(response.get('error', '')):
                        logger.warning(f"触发限流，等待2秒后重试该页面...")
                        time.sleep(2)  # 遇到限流时额外等待
                        # 重新尝试该页面
                        continue
                    
                    break  # 暂停该市场的同步，继续下一个市场
                
                # 处理返回的数据
                keyword_data_list = response.get('data', [])
                if not keyword_data_list:
                    logger.warning(f"市场 {market_id} 第 {page_num} 页未获取到SP广告关键词数据")
                else:
                    sync_log.total_count += len(keyword_data_list)
                    total_processed_for_market += len(keyword_data_list)
                    logger.info(f"成功获取市场ID {market_id} 第 {page_num} 页数据，共 {len(keyword_data_list)} 条，累计处理 {total_processed_for_market} 条")
                
                # 处理每条关键词数据
                for idx, keyword_data in enumerate(keyword_data_list):
                    try:
                        # 映射API返回的数据到模型字段
                        keyword_product_data = {
                            **map_sp_kw_data(keyword_data),
                        }
                        
                        # 处理日期字段
                        if 'createDate' in keyword_data:
                            try:
                                keyword_product_data['create_date'] = datetime.strptime(keyword_data['createDate'], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                logger.warning(f"无法解析createDate: {keyword_data.get('createDate')}")
                        
                        if not keyword_product_data.get('create_date'):
                            keyword_product_data['create_date'] = timezone.now().date()
                        
                        # 检查必要字段
                        if not keyword_product_data.get('keyword_id'):
                            error_msg = f"关键词数据缺少keyword_id字段: {keyword_data}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            failed_count += 1
                            continue
                        
                        # 创建或更新关键词记录
                        try:
                            ads_keyword, created = AdsSpKeyword.objects.update_or_create(
                                market_id=keyword_product_data.get('market_id'),
                                # portfolio_id=keyword_product_data.get('portfolioId'),
                                create_date=keyword_product_data.get('create_date'),
                                match_type=keyword_product_data.get('match_type'),
                                campaign_id=keyword_product_data.get('campaign_id'),
                                group_id=keyword_product_data.get('group_id'),
                                keyword_id=keyword_product_data.get('keyword_id'),
                                defaults=keyword_product_data
                            )
                            
                            ads_keyword.save()
                            success_count += 1
                            logger.debug(f"处理关键词数据成功: Keyword={keyword_product_data.get('keyword_text')}, Campaign={keyword_product_data.get('campaign_name')}")
                            
                        except Exception as db_error:
                            error_msg = f"数据库保存失败: {str(db_error)}, 数据: {keyword_product_data}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            failed_count += 1
                            
                    except Exception as e:
                        error_msg = f"处理关键词数据时发生异常: {str(e)}, 索引: {idx}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                
                # 更新分页参数
                next_id = response.get('next_id')
                has_more = response.get('has_more', False)
                logger.debug(f"更新分页参数 - next_id: {next_id}, has_more: {has_more}")
                page_num += 1
        
        # 更新同步日志
        sync_log.status = 'success' if failed_count == 0 else 'partial_success'
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        # 保存详细错误信息，但限制长度
        if detailed_errors:
            # 只保存前5个错误详情，避免字段过长
            sync_log.error_message = '\n'.join(detailed_errors[:5]) + (f"\n... 还有{len(detailed_errors)-5}个错误" if len(detailed_errors) > 5 else '')
        sync_log.end_time = timezone.now()
        sync_log.save()
        logger.info(f"SP广告关键词数据同步完成，批次ID: {sync_log.id}，成功 {success_count} 条，失败 {failed_count} 条")
        
        return Response({
            'status': 'success',
            'message': f'SP广告关键词数据同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SP广告关键词数据同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.error_message += '\n详细错误: ' + '\n'.join(detailed_errors[:5])
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'SP广告关键词数据同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 在get_sp_ad_data函数后添加以下代码
@api_view(['GET'])
@permission_classes([AllowAny])
def get_sp_kw_data(request):
    """获取SP广告关键词数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        keyword_text = request.GET.get('keywordText')
        campaign_id = request.GET.get('campaignId')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSpKeyword.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if keyword_text:
            queryset = queryset.filter(keyword_text__icontains=keyword_text)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for keyword in queryset:
            result.append({
                'id': keyword.id,
                'keywordId': keyword.keyword_id,
                'keywordText': keyword.keyword_text,
                'marketId': keyword.market_id,
                'campaignId': keyword.campaign_id,
                'campaignName': keyword.campaign_name,
                'groupName': keyword.group_name,
                'matchType': keyword.match_type,
                'bid': float(keyword.bid),
                'impressions': keyword.impressions,
                'clicks': keyword.clicks,
                'cost': float(keyword.cost),
                'adsSales': float(keyword.ads_sales),
                'ctr': float(keyword.ctr) if keyword.ctr else 0,
                'cpc': float(keyword.cpc) if keyword.cpc else 0,
                'acos': float(keyword.acos) if keyword.acos else 0,
                'roas': float(keyword.roas) if keyword.roas else 0,
                'reportDate': keyword.report_date.strftime('%Y-%m-%d'),
                'createDate': keyword.create_date.strftime('%Y-%m-%d') if keyword.create_date else None,
                'servingStatus': keyword.serving_status,
                'state': keyword.state
            })
        
        return Response({
            'success': True,
            'data': {
                'keywords': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取SP广告关键词数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 映射SP广告目标数据
def map_sp_target_data(target_data):
    """将Gerpgo返回的SP广告目标数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    mapped_data = {
        'market_id': target_data.get('marketId'),
        'portfolio_id': target_data.get('portfolioId'),
        'portfolio_name': target_data.get('portfolioName'),
        'campaign_id': target_data.get('campaignId'),
        'campaign_name': target_data.get('campaignName'),
        'group_id': target_data.get('groupId'),
        'group_name': target_data.get('groupName'),
        'target_id': target_data.get('targetId'),
        'targeting_text': target_data.get('targetingText'),
        'targeting_type': target_data.get('targetingType'),
        'query': target_data.get('query'),
        'impressions': target_data.get('impressions'),
        'clicks': target_data.get('clicks'),
        'cost': target_data.get('cost'),
        'ads_orders': target_data.get('adsOrders'),
        'ads_sales': target_data.get('adsSales'),
        'create_date': target_data.get('createDate'),
    }

    return mapped_data

# 同步SP广告投放数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sp_target_data_from_gerpgo(request):
    """从Gerpgo同步SP广告目标数据"""
    # 验证请求数据
    serializer = SPTargetDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SPTarget数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    # 获取日期参数，同时支持两种命名方式
    start_date = data.get('start_date') or data.get('startDataDate')
    end_date = data.get('end_date') or data.get('endDataDate')
    
    # 如果没有日期参数，默认使用近7天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        logger.info(f"未提供日期参数，默认使用近7天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sp_target_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SP广告目标数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SPTarget数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SP广告目标数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 分页获取所有数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的第 {page_num} 页数据")
                
                # 构建请求参数
                params = {
                    'marketId': market_id,
                    'count': count
                }
                
                # 添加nextId参数
                if next_id is not None:
                    params['nextId'] = next_id
                    logger.debug(f"当前分页参数 - nextId: {next_id}")
                
                if start_date:
                    params['startDataDate'] = start_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置开始日期: {params['startDataDate']}")
                if end_date:
                    params['endDataDate'] = end_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置结束日期: {params['endDataDate']}")
                
                # 调用API获取数据
                success, response = client.get_sp_target(**params)
                
                # 增加延迟，确保符合每1秒1次的限流规则
                import time
                time.sleep(1.1)  # 增加1.1秒延迟，确保不超过限流
                
                if not success:
                    error_msg = f"获取市场 {market_id} 的SP广告目标数据失败: {response.get('error', '未知错误')}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    
                    # 检查是否为限流错误（509）
                    if '接口调用次数已超过限制次数' in str(response.get('error', '')):
                        logger.warning(f"触发限流，等待2秒后重试该页面...")
                        time.sleep(2)  # 遇到限流时额外等待
                        # 重新尝试该页面
                        continue
                    
                    break  # 暂停该市场的同步，继续下一个市场
                
                # 处理返回的数据
                target_data_list = response.get('data', [])
                if not target_data_list:
                    logger.warning(f"市场 {market_id} 第 {page_num} 页未获取到SP广告目标数据")
                else:
                    sync_log.total_count += len(target_data_list)
                    total_processed_for_market += len(target_data_list)
                    logger.info(f"成功获取市场ID {market_id} 第 {page_num} 页数据，共 {len(target_data_list)} 条，累计处理 {total_processed_for_market} 条")
                
                # 处理每条目标数据
                for idx, target_data in enumerate(target_data_list):
                    try:
                        # 映射API返回的数据到模型字段
                        target_mapped_data = map_sp_target_data(target_data)
                        
                        # 处理日期字段
                        if 'create_date' in target_mapped_data and target_mapped_data['create_date']:
                            try:
                                target_mapped_data['create_date'] = datetime.strptime(target_mapped_data['create_date'], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                logger.warning(f"无法解析createDate: {target_mapped_data.get('create_date')}")
                                target_mapped_data['create_date'] = None
                        
                        if not target_mapped_data.get('create_date'):
                            target_mapped_data['create_date'] = timezone.now().date()
                        elif isinstance(target_mapped_data['create_date'], str):
                            try:
                                target_mapped_data['create_date'] = datetime.strptime(target_mapped_data['create_date'], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                logger.warning(f"无法解析createDate: {target_mapped_data.get('create_date')}")
                                target_mapped_data['create_date'] = timezone.now().date()
                        
                        # 检查必要字段
                        if not target_mapped_data.get('target_id'):
                            error_msg = f"目标数据缺少target_id字段: {target_data}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            failed_count += 1
                            continue
                        
                        # 创建或更新目标记录
                        try:
                            ads_target, created = AdsSpTarget.objects.update_or_create(
                                market_id=target_mapped_data.get('market_id'),
                                # portfolio_id=target_mapped_data.get('portfolio_id'),
                                campaign_id=target_mapped_data.get('campaign_id'),
                                group_id=target_mapped_data.get('group_id'),
                                target_id=target_mapped_data.get('target_id'),
                                targeting_type=target_mapped_data.get('targeting_type'),
                                query=target_mapped_data.get('query'),
                                create_date=target_mapped_data.get('create_date'),
                                defaults=target_mapped_data
                            )
                            
                            ads_target.save()
                            success_count += 1
                            logger.debug(f"处理目标数据成功: Target={target_mapped_data.get('targeting_text')}, Campaign={target_mapped_data.get('campaign_name')}")
                            
                        except Exception as db_error:
                            error_msg = f"数据库保存失败: {str(db_error)}, 数据: {target_mapped_data}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            failed_count += 1
                            
                    except Exception as e:
                        error_msg = f"处理目标数据时发生异常: {str(e)}, 索引: {idx}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                
                # 更新分页参数
                next_id = response.get('next_id')
                has_more = response.get('has_more', False)
                logger.debug(f"更新分页参数 - next_id: {next_id}, has_more: {has_more}")
                page_num += 1
        
        # 更新同步日志
        sync_log.status = 'success' if failed_count == 0 else 'partial_success'
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        # 保存详细错误信息，但限制长度
        if detailed_errors:
            # 只保存前5个错误详情，避免字段过长
            sync_log.error_message = '\n'.join(detailed_errors[:5]) + (f"\n... 还有{len(detailed_errors)-5}个错误" if len(detailed_errors) > 5 else '')
        sync_log.end_time = timezone.now()
        sync_log.save()
        logger.info(f"SP广告目标数据同步完成，批次ID: {sync_log.id}，成功 {success_count} 条，失败 {failed_count} 条")
        
        return Response({
            'status': 'success',
            'message': f'SP广告目标数据同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SP广告目标数据同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.error_message += '\n详细错误: ' + '\n'.join(detailed_errors[:5])
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'SP广告目标数据同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 在get_sp_kw_data函数后添加以下代码
@api_view(['GET'])
@permission_classes([AllowAny])
def get_sp_target_data(request):
    """获取SP广告目标数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        targeting_text = request.GET.get('targetingText')
        campaign_id = request.GET.get('campaignId')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSpTarget.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if targeting_text:
            queryset = queryset.filter(targeting_text__icontains=targeting_text)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for target in queryset:
            result.append({
                'id': target.id,
                'targetId': target.target_id,
                'targetingText': target.targeting_text,
                'marketId': target.market_id,
                'campaignId': target.campaign_id,
                'campaignName': target.campaign_name,
                'groupName': target.group_name,
                'targetingType': target.targeting_type,
                'bid': float(target.bid),
                'impressions': target.impressions,
                'clicks': target.clicks,
                'cost': float(target.cost),
                'adsSales': float(target.ads_sales),
                'ctr': float(target.ctr) if target.ctr else 0,
                'cpc': float(target.cpc) if target.cpc else 0,
                'acos': float(target.acos) if target.acos else 0,
                'roas': float(target.roas) if target.roas else 0,
                'reportDate': target.report_date.strftime('%Y-%m-%d'),
                'createDate': target.create_date.strftime('%Y-%m-%d') if target.create_date else None,
                'servingStatus': target.serving_status,
                'state': target.state
            })
        
        return Response({
            'success': True,
            'data': {
                'targets': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取SP广告目标数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 映射SP广告展示位置数据
def map_sp_placement_data(placement_data):
    """将Gerpgo返回的SP广告展示位置数据映射为统一格式"""
    return {
        'market_id': placement_data.get('market_id'),
        'portfolio_id': placement_data.get('portfolioId'),
        'portfolio_name': placement_data.get('portfolioName'),
        'campaign_id': placement_data.get('campaignId'),
        'campaign_name': placement_data.get('campaignName'),
        'campaign_type': placement_data.get('campaignType'),
        'targeting_type': placement_data.get('targetingType'),
        'state': placement_data.get('state'),
        'serving_status': placement_data.get('servingStatus'),
        'daily_budget': placement_data.get('dailyBudget'),
        'start_date': placement_data.get('startDate'),
        'end_date': placement_data.get('endDate'),
        'create_date': placement_data.get('createDate'),
        'placement': placement_data.get('placement'),
        'bid_strategy': placement_data.get('bidStrategy'),
        'bid_strategy_name': placement_data.get('bidStrategyName'),
        'rule_roas': placement_data.get('ruleRoas'),
        'bid_adjustment': placement_data.get('bidAdjustment'),
        'bid_adjustment_name': placement_data.get('bidAdjustmentName'),
        'bidding':placement_data.get('bidding'),
        'impressions': placement_data.get('impressions'),
        'clicks': placement_data.get('clicks'),
        'cost': placement_data.get('cost'),
        'ads_orders': placement_data.get('adsOrders'),
        'ads_sales': placement_data.get('adsSales'),
        'ads_product_orders': placement_data.get('adsProductOrders'),
        'ads_product_sales': placement_data.get('adsProductSales'),
        'other_product_sales': placement_data.get('otherProductSales'),
    }

# 同步SP广告展示位置数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sp_placement_data_from_gerpgo(request):
    """从Gerpgo同步SP广告展示位置数据"""
    # 验证请求数据
    serializer = SPPlacementDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SPPlacement数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    # 获取日期参数，同时支持两种命名方式
    start_date = data.get('start_date') or data.get('startDataDate')
    end_date = data.get('end_date') or data.get('endDataDate')
    
    # 如果没有日期参数，默认使用近7天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        logger.info(f"未提供日期参数，默认使用近7天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sp_placement_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SP广告展示位置数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SPPlacement数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SP广告展示位置数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 循环获取分页数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的SP广告展示位置数据 - 第 {page_num} 页，next_id: {next_id}")
                
                # 调用API获取数据
                success, result = client.get_sp_placement(
                    market_ids=market_id,
                    count=count,
                    next_id=next_id,
                    start_data_date=start_date,
                    end_data_date=end_date
                )
                
                # 处理限流错误
                if not success and isinstance(result, dict) and result.get('status_code') == 429:
                    logger.warning(f"请求触发限流，等待2秒后重试")
                    time.sleep(2)  # 额外等待2秒后重试
                    continue
                
                # 处理其他错误
                if not success:
                    error_msg = f"获取市场ID {market_id} 的SP广告展示位置数据失败: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 检查结果格式
                if not isinstance(result, dict):
                    error_msg = f"获取市场ID {market_id} 的SP广告展示位置数据结果格式不正确: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 提取数据和分页信息
                placement_data_list = result.get('data', [])
                next_id = result.get('next_id')
                has_more = result.get('has_more', False)
                
                logger.info(f"成功获取市场ID {market_id} 的SP广告展示位置数据 - 第 {page_num} 页，共 {len(placement_data_list)} 条")
                
                # 处理每一条数据
                for placement_data in placement_data_list:
                    try:
                        # 映射数据格式
                        mapped_data = map_sp_placement_data(placement_data)
                        
                        # 处理日期字段
                        if 'create_date' in mapped_data and mapped_data['create_date']:
                            mapped_data['create_date'] = datetime.strptime(mapped_data['create_date'], '%Y-%m-%d').date()
                        if 'start_date' in mapped_data and mapped_data['start_date']:
                            mapped_data['start_date'] = datetime.strptime(mapped_data['start_date'], '%Y-%m-%d').date()
                        if 'end_date' in mapped_data and mapped_data['end_date']:
                            mapped_data['end_date'] = datetime.strptime(mapped_data['end_date'], '%Y-%m-%d').date()
                       
                        
                        # 使用update_or_create避免重复数据
                        obj, created = AdsSpPlacement.objects.update_or_create(
                            market_id=mapped_data['market_id'],
                            create_date=mapped_data['create_date'],
                            # portfolio_id=mapped_data['portfolio_id'],
                            campaign_id=mapped_data['campaign_id'],
                            placement=mapped_data['placement'],
                            defaults=mapped_data
                        )
                        
                        success_count += 1
                        total_processed_for_market += 1
                        
                    except Exception as e:
                        error_msg = f"处理市场ID {market_id} 的SP广告展示位置数据时发生错误: {str(e)}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                
                # 更新分页信息
                page_num += 1
                
                # 确保has_more的正确性
                if not placement_data_list or len(placement_data_list) < count:
                    has_more = False
                    logger.info(f"市场ID {market_id} 的SP广告展示位置数据已全部获取完毕，共处理 {total_processed_for_market} 条")
            
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = success_count + failed_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        logger.info(f"SP广告展示位置数据同步完成，成功 {success_count} 条，失败 {failed_count} 条")
        
        # 返回成功响应
        return Response({
            'status': 'success',
            'message': f'SP广告展示位置数据同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SP广告展示位置数据同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.error_message += '\n详细错误: ' + '\n'.join(detailed_errors[:5])
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'SP广告展示位置数据同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 添加前端数据接口
@api_view(['GET'])
@permission_classes([AllowAny])
def get_sp_placement_data(request):
    """获取SP广告展示位置数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        placement = request.GET.get('placement')
        campaign_id = request.GET.get('campaignId')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSpPlacement.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if placement:
            queryset = queryset.filter(placement__icontains=placement)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if start_date:
            queryset = queryset.filter(create_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(create_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for placement_obj in queryset:
            result.append({
                'id': placement_obj.id,
                'placement': placement_obj.placement,
                'marketId': placement_obj.market_id,
                'campaignId': placement_obj.campaign_id,
                'campaignName': placement_obj.campaign_name,
                'targetingType': placement_obj.targeting_type,
                'dailyBudget': float(placement_obj.daily_budget),
                'impressions': placement_obj.impressions,
                'clicks': placement_obj.clicks,
                'cost': float(placement_obj.cost),
                'adsSales': float(placement_obj.ads_sales),
                'ctr': float(placement_obj.ctr) if placement_obj.ctr else 0,
                'cpc': float(placement_obj.cpc) if placement_obj.cpc else 0,
                'acos': float(placement_obj.acos) if placement_obj.acos else 0,
                'roas': float(placement_obj.roas) if placement_obj.roas else 0,
                'reportDate': placement_obj.report_date.strftime('%Y-%m-%d'),
                'createDate': placement_obj.create_date.strftime('%Y-%m-%d') if placement_obj.create_date else None,
                'servingStatus': placement_obj.serving_status,
                'state': placement_obj.state
            })
        
        return Response({
            'success': True,
            'data': {
                'placements': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取SP广告展示位置数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 映射SP广告搜索词数据
def map_sp_search_terms_data(search_term_data):
    """将Gerpgo返回的SP广告搜索词数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': search_term_data.get('marketId'),
        'portfolio_id': search_term_data.get('portfolioId'),
        'portfolio_name': search_term_data.get('portfolioName'),
        'campaign_id': search_term_data.get('campaignId'),
        'campaign_name': search_term_data.get('campaignName'),
        'group_id': search_term_data.get('groupId'),
        'group_name': search_term_data.get('groupName'),
        'keyword_id': search_term_data.get('keywordId'),
        'keyword_text': search_term_data.get('keywordText'),
        'query': search_term_data.get('query'),
        'match_type': search_term_data.get('matchType'),
        'impressions': search_term_data.get('impressions'),
        'clicks': search_term_data.get('clicks'),
        'cost': search_term_data.get('cost'),
        'ads_orders': search_term_data.get('adsOrders'),
        'ads_sales': search_term_data.get('adsSales'),
        'create_date': search_term_data.get('createDate'),
    }


# 同步SP广告搜索词数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sp_search_terms_data_from_gerpgo(request):
    """从Gerpgo同步SP广告搜索词数据"""
    # 验证请求数据
    serializer = SPSearchTermsDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SPSearchTerms数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    start_date = data.get('startDataDate')
    end_date = data.get('endDataDate')
    
    # 如果没有日期参数，默认使用近7天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        logger.info(f"未提供日期参数，默认使用近7天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sp_search_terms_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SP广告搜索词数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SPSearchTerms数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SP广告搜索词数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 循环获取分页数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的SP广告搜索词数据 - 第 {page_num} 页，next_id: {next_id}")
                
                # 调用API获取数据
                success, result = client.get_sp_search_terms(
                    market_ids=market_id,
                    count=count,
                    next_id=next_id,
                    start_data_date=start_date,
                    end_data_date=end_date
                )
                
                # 处理限流错误
                if not success and isinstance(result, dict) and result.get('status_code') == 429:
                    logger.warning(f"请求触发限流，等待2秒后重试")
                    time.sleep(2)  # 额外等待2秒后重试
                    continue
                
                # 处理其他错误
                if not success:
                    error_msg = f"获取市场ID {market_id} 的SP广告搜索词数据失败: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 检查结果格式
                if not isinstance(result, dict):
                    error_msg = f"获取市场ID {market_id} 的SP广告搜索词数据结果格式不正确: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 提取数据和分页信息
                search_term_data_list = result.get('data', [])
                next_id = result.get('next_id')
                has_more = result.get('has_more', False)
                
                logger.info(f"成功获取市场ID {market_id} 的SP广告搜索词数据 - 第 {page_num} 页，共 {len(search_term_data_list)} 条")
                
                # 处理每一条数据
                for search_term_data in search_term_data_list:
                    try:
                        # 映射数据格式
                        mapped_data = map_sp_search_terms_data(search_term_data)
                        
                        # 处理日期字段
                        if 'create_date' in mapped_data and mapped_data['create_date']:
                            mapped_data['create_date'] = datetime.strptime(mapped_data['create_date'], '%Y-%m-%d').date()
                        
                        # 准备更新或创建数据的关键字
                        update_fields = [field for field in mapped_data.keys() if field not in ['market_id', 'create_date', 'portfolio_id', 'campaign_id', 'group_id', 'keyword_id']]
                        
                        # 使用update_or_create避免重复数据
                        obj, created = AdsSpSearchTerms.objects.update_or_create(
                            market_id=mapped_data['market_id'],
                            create_date=mapped_data['create_date'],
                            # portfolio_id=mapped_data['portfolio_id'],
                            campaign_id=mapped_data['campaign_id'],
                            group_id=mapped_data['group_id'],
                            keyword_id=mapped_data['keyword_id'],
                            match_type=mapped_data['match_type'],
                            query=mapped_data['query'],
                            defaults=mapped_data
                        )
                        
                        success_count += 1
                        total_processed_for_market += 1
                        
                    except Exception as e:
                        error_msg = f"处理市场ID {market_id} 的SP广告搜索词数据时发生错误: {str(e)}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                
                # 更新分页信息
                page_num += 1
                
                # 确保has_more的正确性
                if not search_term_data_list or len(search_term_data_list) < count:
                    has_more = False
                    logger.info(f"市场ID {market_id} 的SP广告搜索词数据已全部获取完毕，共处理 {total_processed_for_market} 条")
            
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = success_count + failed_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        logger.info(f"SP广告搜索词数据同步完成，成功 {success_count} 条，失败 {failed_count} 条")
        
        # 返回成功响应
        return Response({
            'status': 'success',
            'message': f'SP广告搜索词数据同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SP广告搜索词数据同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.error_message += '\n详细错误: ' + '\n'.join(detailed_errors[:5])
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'SP广告搜索词数据同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 添加前端数据接口
@api_view(['GET'])
@permission_classes([AllowAny])
def get_sp_search_terms_data(request):
    """获取SP广告搜索词数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        keyword_text = request.GET.get('keywordText')
        query = request.GET.get('query')
        campaign_id = request.GET.get('campaignId')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSpSearchTerms.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if keyword_text:
            queryset = queryset.filter(keyword_text__icontains=keyword_text)
        if query:
            queryset = queryset.filter(query__icontains=query)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for search_term in queryset:
            result.append({
                'id': search_term.id,
                'keywordId': search_term.keyword_id,
                'keywordText': search_term.keyword_text,
                'query': search_term.query,
                'marketId': search_term.market_id,
                'campaignId': search_term.campaign_id,
                'campaignName': search_term.campaign_name,
                'groupName': search_term.group_name,
                'matchType': search_term.match_type,
                'impressions': search_term.impressions,
                'clicks': search_term.clicks,
                'cost': float(search_term.cost),
                'adsSales': float(search_term.ads_sales),
                'ctr': float(search_term.ctr) if search_term.ctr else 0,
                'cpc': float(search_term.cpc) if search_term.cpc else 0,
                'acos': float(search_term.acos) if search_term.acos else 0,
                'roas': float(search_term.roas) if search_term.roas else 0,
                'reportDate': search_term.report_date.strftime('%Y-%m-%d'),
                'createDate': search_term.create_date.strftime('%Y-%m-%d') if search_term.create_date else None,
                'servingStatus': search_term.serving_status,
                'state': search_term.state
            })
        
        return Response({
            'success': True,
            'data': {
                'searchTerms': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取SP广告搜索词数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


def map_sb_kw_data(keyword_data):
    """将Gerpgo返回的SB广告关键词数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': keyword_data.get('marketId'),
        'portfolio_id': keyword_data.get('portfolioId'),
        'portfolio_name': keyword_data.get('portfolioName'),
        'campaign_id': keyword_data.get('campaignId'),
        'campaign_name': keyword_data.get('campaignName'),
        'group_id': keyword_data.get('groupId'),
        'group_name': keyword_data.get('groupName'),
        'keyword_id': keyword_data.get('keywordId'),
        'keyword_text': keyword_data.get('keywordText'),
        'match_type': keyword_data.get('matchType'),
        'state': keyword_data.get('state'),
        'bid': keyword_data.get('bid'),
        'impressions': keyword_data.get('impressions'),
        'clicks': keyword_data.get('clicks'),
        'cost': keyword_data.get('cost'),
        'ads_orders': keyword_data.get('adsOrders'),
        'ads_sales': keyword_data.get('adsSales'),
        'ads_product_orders': keyword_data.get('adsProductOrders'),
        'ads_product_sales': keyword_data.get('adsProductSales'),
        'other_product_sales': keyword_data.get('otherProductSales'),
        'view_impressions': keyword_data.get('viewImpressions'),
        'new_buyer_orders': keyword_data.get('newBuyerOrders'),
        'new_buyer_sales': keyword_data.get('newBuyerSales'),
        'page_views': keyword_data.get('pageViews'),
        'create_date': keyword_data.get('createDate'),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sb_kw_data_from_gerpgo(request):
    """从Gerpgo同步SB广告关键词数据"""
    # 验证请求数据
    serializer = SBKWDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SBKW数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    start_date = data.get('startDataDate')
    end_date = data.get('endDataDate')
    
    # 如果没有日期参数，默认使用近14天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sb_kw_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SB广告关键词数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SBKW数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SB广告关键词数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 分页获取所有数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的第 {page_num} 页数据")
                
                # 构建请求参数
                params = {
                    'marketId': market_id,
                    'count': count
                }
                
                # 添加nextId参数
                if next_id is not None:
                    params['nextId'] = next_id
                    logger.debug(f"当前分页参数 - nextId: {next_id}")
                
                if start_date:
                    params['startDataDate'] = start_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置开始日期: {params['startDataDate']}")
                if end_date:
                    params['endDataDate'] = end_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置结束日期: {params['endDataDate']}")
                
                # 调用API获取数据
                success, response = client.get_sb_keywords(**params)
                
                # 增加延迟，确保符合每1秒1次的限流规则
                import time
                time.sleep(1.1)  # 增加1.1秒延迟，确保不超过限流
                
                if not success:
                    error_msg = f"获取市场 {market_id} 的SB广告关键词数据失败: {response.get('error', '未知错误')}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 提取数据
                keyword_data_list = response.get('data', [])
                next_id = response.get('nextId')
                has_more = response.get('hasMore', False)
                
                logger.info(f"获取到 {len(keyword_data_list)} 条SB广告关键词数据，nextId: {next_id}, hasMore: {has_more}")
                
                if not keyword_data_list:
                    logger.info(f"市场 {market_id} 的第 {page_num} 页没有数据")
                    page_num += 1
                    continue
                
                # 处理每一条关键词数据
                for keyword_data in keyword_data_list:
                    try:
                        # 映射数据
                        mapped_data = map_sb_kw_data(keyword_data)
                        
                        # 创建或更新AdsSbKeyword对象
                        ads_sb_keyword, created = AdsSbKeyword.objects.update_or_create(
                            market_id=mapped_data['market_id'],  # 确保关联到正确的市场ID
                            # portfolio_id=mapped_data.get('portfolio_id'),  # 确保关联到正确的组合ID
                            campaign_id=mapped_data.get('campaign_id'),  # 确保关联到正确的活动ID
                            group_id=mapped_data.get('group_id'),  # 确保关联到正确的分组ID
                            keyword_id=mapped_data.get('keyword_id'),  # 确保关联到正确的关键词ID
                            match_type=mapped_data.get('match_type'),  # 确保关联到正确的匹配类型
                            create_date=mapped_data.get('create_date'),  # 确保关联到正确的创建日期
                            defaults=mapped_data
                        )
                        
                        if created:
                            logger.debug(f"创建新的SB广告关键词记录: {mapped_data['keyword_text']}")
                        else:
                            logger.debug(f"更新SB广告关键词记录: {mapped_data['keyword_text']}")
                        
                        success_count += 1
                        total_processed_for_market += 1
                        
                    except Exception as e:
                        error_msg = f"处理SB广告关键词数据失败: {str(e)}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                
                page_num += 1
                
            logger.info(f"市场ID {market_id} 的SB广告关键词数据处理完成，共处理 {total_processed_for_market} 条数据")
        
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = success_count + failed_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        logger.info(f"SB广告关键词数据同步完成，总处理 {sync_log.total_count} 条，成功 {sync_log.success_count} 条，失败 {sync_log.failed_count} 条")
        
        return Response({
            'success': True,
            'message': 'SB广告关键词数据同步成功',
            'data': {
                'total_count': sync_log.total_count,
                'success_count': sync_log.success_count,
                'failed_count': sync_log.failed_count
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # 更新同步日志状态为失败
        sync_log.status = 'failed'
        sync_log.failed_count += 1
        sync_log.detailed_error = str(e)
        sync_log.save()
        
        logger.error(f"SB广告关键词数据同步异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'data': {
                'total_count': sync_log.total_count,
                'success_count': sync_log.success_count,
                'failed_count': sync_log.failed_count
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_sb_kw_data(request):
    """获取SB广告关键词数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        keyword_text = request.GET.get('keywordText')
        campaign_id = request.GET.get('campaignId')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSbKeyword.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if keyword_text:
            queryset = queryset.filter(keyword_text__icontains=keyword_text)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for keyword in queryset:
            result.append({
                'id': keyword.id,
                'keywordId': keyword.keyword_id,
                'keywordText': keyword.keyword_text,
                'marketId': keyword.market_id,
                'campaignId': keyword.campaign_id,
                'campaignName': keyword.campaign_name,
                'groupName': keyword.group_name,
                'matchType': keyword.match_type,
                'bid': float(keyword.bid),
                'impressions': keyword.impressions,
                'clicks': keyword.clicks,
                'cost': float(keyword.cost),
                'adsSales': float(keyword.ads_sales),
                'ctr': float(keyword.ctr) if keyword.ctr else 0,
                'cpc': float(keyword.cpc) if keyword.cpc else 0,
                'acos': float(keyword.acos) if keyword.acos else 0,
                'roas': float(keyword.roas) if keyword.roas else 0,
                'reportDate': keyword.report_date.strftime('%Y-%m-%d'),
                'createDate': keyword.create_date.strftime('%Y-%m-%d') if keyword.create_date else None,
                'servingStatus': keyword.serving_status,
                'state': keyword.state
            })
        
        return Response({
            'success': True,
            'data': {
                'keywords': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
        
    except Exception as e:
        logger.error(f"获取SB广告关键词数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 映射SB广告活动数据
def map_sb_campaign_data(campaign_data, market_id):
    """将Gerpgo返回的SB广告活动数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': market_id,
        'portfolio_id': campaign_data.get('portfolioId'),
        'portfolio_name': campaign_data.get('portfolioName'),
        'campaign_id': campaign_data.get('campaignId'),
        'campaign_name': campaign_data.get('campaignName'),
        'targeting_type': campaign_data.get('targetingType'),
        'ads_type': campaign_data.get('adsType'),
        'budget_type': campaign_data.get('budgetType'),
        'budget': campaign_data.get('budget'),
        'state': campaign_data.get('state'),
        'serving_status': campaign_data.get('servingStatus'),
        'start_date': campaign_data.get('startDate'),
        'end_date': campaign_data.get('endDate'),
        'impressions': campaign_data.get('impressions', 0),
        'clicks': campaign_data.get('clicks', 0),
        'cost': campaign_data.get('cost', 0),
        'ads_orders': campaign_data.get('adsOrders', 0),
        'ads_sales': campaign_data.get('adsSales', 0),
        'ads_product_orders': campaign_data.get('adsProductOrders', 0),
        'ads_product_sales': campaign_data.get('adsProductSales', 0),
        'other_product_sales': campaign_data.get('otherProductSales', 0),
        'view_impressions': campaign_data.get('viewImpressions', 0),
        'new_buyer_orders': campaign_data.get('newBuyerOrders', 0),
        'new_buyer_sales': campaign_data.get('newBuyerSales', 0),
        'page_views': campaign_data.get('pageViews', 0),
        'create_date': campaign_data.get('createDate')
    }


# 添加正确的装饰器
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sb_campaign_data_from_gerpgo(request):
    """从Gerpgo同步SB Campaign数据"""
    # 验证请求参数
    serializer = SBCampainDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SB Campaign数据同步请求参数验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    request_market_ids = validated_data.get('marketIds')
    count = validated_data.get('count', 100)
    start_data_date = validated_data.get('startDataDate')
    end_data_date = validated_data.get('endDataDate')
    
    # 如果没有日期参数，默认使用近14天
    if not start_data_date and not end_data_date:
        end_data_date = datetime.now()
        start_data_date = end_data_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_data_date.strftime('%Y-%m-%d')}，结束日期: {end_data_date.strftime('%Y-%m-%d')}")
    
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
            # 如果数据库中也没有市场ID，则返回错误
            if not market_ids:
                logger.error("数据库中没有可用的市场ID")
                raise ValueError("市场ID列表不能为空，请先同步店铺信息")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
        
    # 创建同步日志 - 使用正确的字段名称
    sync_log = SyncLog.objects.create(
        sync_type='sb_campaign_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SB Campaign数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端 - 传递完整参数
        gerpgo_client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 统计信息
        total_success = 0
        total_fail = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 遍历市场ID
        for market_id in market_ids:
            logger.info(f"开始同步市场ID {market_id} 的SB Campaign数据")
            
            # 分页获取数据
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            while has_more:
                logger.info(f"获取市场ID {market_id} 的第 {page_num} 页数据")
                
                # 构建请求参数 - 使用字典形式更灵活
                params = {
                    'marketId': market_id,
                    'count': count
                }
                
                # 添加nextId参数
                if next_id is not None:
                    params['next_id'] = next_id
                    logger.debug(f"当前分页参数 - nextId: {next_id}")
                
                if start_data_date:
                    params['start_data_date'] = start_data_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置开始日期: {params['start_data_date']}")
                if end_data_date:
                    params['end_data_date'] = end_data_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置结束日期: {params['end_data_date']}")
                
                # 调用API获取数据
                success, result = gerpgo_client.get_sb_campaign(**params)
                
                # 增加延迟，确保符合每1秒1次的限流规则
                import time
                time.sleep(1.1)
                
                if not success:
                    error_msg = f"获取市场ID {market_id} 的SB Campaign数据失败: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    total_fail += 1
                    has_more = False
                    continue
                
                # 处理获取到的数据
                if 'data' in result and result['data']:
                    sb_campaign_data_list = result['data']
                    total_processed_for_market += len(sb_campaign_data_list)
                    
                    logger.info(f"获取到 {len(sb_campaign_data_list)} 条SB Campaign数据，nextId: {next_id}, hasMore: {has_more}")
                    
                    # 批量保存数据
                    for sb_campaign_data in sb_campaign_data_list:
                        try:
                            # 使用map_sb_campaign_data函数构建数据字典
                            campaign_data = map_sb_campaign_data(sb_campaign_data, market_id)
                            
                            # 使用update_or_create避免重复数据
                            ads_sb_campaign, created = AdsSbCampaign.objects.update_or_create(
                                market_id=campaign_data['market_id'],
                                # portfolio_id=campaign_data['portfolio_id'],
                                campaign_id=campaign_data['campaign_id'],
                                create_date=campaign_data['create_date'],
                                defaults=campaign_data
                            )
                            
                            if created:
                                logger.debug(f"创建新的SB Campaign记录: {campaign_data['campaign_name']}")
                            else:
                                logger.debug(f"更新SB Campaign记录: {campaign_data['campaign_name']}")
                            
                            total_success += 1
                            
                        except Exception as e:
                            error_msg = f"处理SB Campaign数据时出错: {str(e)}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            total_fail += 1
                            continue
                    
                    # 更新分页信息
                    next_id = result.get('next_id')
                    has_more = result.get('has_more', False)
                    
                else:
                    # 没有数据了
                    has_more = False
                    logger.info(f"市场 {market_id} 的第 {page_num} 页没有数据")
                
                page_num += 1
                
            logger.info(f"市场ID {market_id} 的SB Campaign数据同步完成，共处理 {total_processed_for_market} 条数据")
        
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = total_success + total_fail
        sync_log.success_count = total_success
        sync_log.failed_count = total_fail
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        logger.info(f"SB Campaign数据同步完成，总处理 {sync_log.total_count} 条，成功 {sync_log.success_count} 条，失败 {sync_log.failed_count} 条")
        
        return Response({
            'success': True,
            'message': 'SB Campaign数据同步成功',
            'data': {
                'total_count': sync_log.total_count,
                'success_count': sync_log.success_count,
                'failed_count': sync_log.failed_count
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # 确保sync_log变量已定义
        if 'sync_log' in locals():
            # 更新同步日志状态为失败
            sync_log.status = 'failed'
            sync_log.failed_count += 1
            # 检查是否有detailed_error字段，如果没有则不设置
            if hasattr(sync_log, 'detailed_error'):
                sync_log.detailed_error = str(e)
            sync_log.save()
        
        logger.error(f"SB Campaign数据同步异常: {str(e)}")
        
        # 如果sync_log存在，返回同步日志信息，否则返回基本错误信息
        if 'sync_log' in locals():
            return Response({
                'success': False,
                'error': str(e),
                'data': {
                    'total_count': sync_log.total_count,
                    'success_count': sync_log.success_count,
                    'failed_count': sync_log.failed_count
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'success': False,
                'error': str(e),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_sb_campaign_data(request):
    """获取SB广告活动数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        campaign_id = request.GET.get('campaignId')
        campaign_name = request.GET.get('campaignName')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSbCampaign.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if campaign_name:
            queryset = queryset.filter(campaign_name__icontains=campaign_name)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for campaign in queryset:
            result.append({
                'id': campaign.id,
                'campaignId': campaign.campaign_id,
                'campaignName': campaign.campaign_name,
                'marketId': campaign.market_id,
                'portfolioId': campaign.portfolio_id,
                'portfolioName': campaign.portfolio_name,
                'state': campaign.state,
                'adsType': campaign.ads_type,
                'servingStatus': campaign.serving_status,
                'targetingType': campaign.targeting_type,
                'budgetType': campaign.budget_type,
                'budget': float(campaign.budget),
                'impressions': campaign.impressions,
                'viewImpressions': campaign.view_impressions,
                'clicks': campaign.clicks,
                'pageViews': campaign.page_views,
                'cost': float(campaign.cost),
                'adsSales': float(campaign.ads_sales),
                'adsProductSales': float(campaign.ads_product_sales),
                'otherProductSales': float(campaign.other_product_sales),
                'newBuyerSales': float(campaign.new_buyer_sales),
                'adsOrders': campaign.ads_orders,
                'adsProductOrders': campaign.ads_product_orders,
                'newBuyerOrders': campaign.new_buyer_orders,
                'ctr': float(campaign.ctr) if campaign.ctr else 0,
                'cpc': float(campaign.cpc) if campaign.cpc else 0,
                'cpa': float(campaign.cpa) if campaign.cpa else 0,
                'cvr': float(campaign.cvr) if campaign.cvr else 0,
                'acos': float(campaign.acos) if campaign.acos else 0,
                'roas': float(campaign.roas) if campaign.roas else 0,
                'cpv': float(campaign.cpv) if campaign.cpv else 0,
                'newBuyerOrderRatio': float(campaign.new_buyer_order_ratio) if campaign.new_buyer_order_ratio else 0,
                'newBuyerSaleRatio': float(campaign.new_buyer_sale_ratio) if campaign.new_buyer_sale_ratio else 0,
                'createDate': campaign.create_date.strftime('%Y-%m-%d') if campaign.create_date else None,
                'startDate': campaign.start_date.strftime('%Y-%m-%d') if campaign.start_date else None,
                'endDate': campaign.end_date.strftime('%Y-%m-%d') if campaign.end_date else None,
                'reportDate': campaign.report_date.strftime('%Y-%m-%d'),
                'asins': campaign.asins
            })
        
        return Response({
            'success': True,
            'data': {
                'campaigns': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
        
    except Exception as e:
        logger.error(f"获取SB广告活动数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 映射SB广告创意数据
def map_sb_creative_data(creative_data):
    """将Gerpgo返回的SB广告创意数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': creative_data.get('marketId'),
        'portfolio_id': creative_data.get('portfolioId'),
        'portfolio_name': creative_data.get('portfolioName'),
        'campaign_id': creative_data.get('campaignId'),
        'campaign_name': creative_data.get('campaignName'),
        'group_id': creative_data.get('groupId'),
        'group_name': creative_data.get('groupName'),
        'ad_id': creative_data.get('adId'),
        'ad_name': creative_data.get('adName'),
        'ads_type': creative_data.get('adsType'),
        'creative_type': creative_data.get('creativeType'),
        'asins': creative_data.get('asins'),
        'state': creative_data.get('state'),
        'serving_status': creative_data.get('servingStatus'),
        'impressions': creative_data.get('impressions', 0),
        'clicks': creative_data.get('clicks', 0),
        'cost': creative_data.get('cost', 0),
        'ads_orders': creative_data.get('adsOrders', 0),
        'ads_sales': creative_data.get('adsSales', 0),
        'ads_product_orders': creative_data.get('adsProductOrders', 0),
        'ads_product_sales': creative_data.get('adsProductSales', 0),
        'other_product_sales': creative_data.get('otherProductSales', 0),
        'view_impressions': creative_data.get('viewImpressions', 0),
        'new_buyer_orders': creative_data.get('newBuyerOrders', 0),
        'new_buyer_sales': creative_data.get('newBuyerSales', 0),
        'page_views': creative_data.get('pageViews', 0),
        'create_date': creative_data.get('createDate'),
    }

@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sb_creative_data_from_gerpgo(request):
    """从Gerpgo同步SB广告创意数据"""
    # 验证请求数据
    serializer = SBCreativeDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SBCreative数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    start_date = data.get('startDataDate')
    end_date = data.get('endDataDate')

    # 如果没有日期参数，默认使用近14天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sb_creative_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SB广告创意数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SPCreative数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SB广告创意数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 分页获取所有数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的第 {page_num} 页数据")
                
                # 构建请求参数
                params = {
                    'marketId': market_id,
                    'count': count
                }
                
                # 添加nextId参数
                if next_id is not None:
                    params['nextId'] = next_id
                    logger.debug(f"当前分页参数 - nextId: {next_id}")
                
                if start_date:
                    params['startDataDate'] = start_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置开始日期: {params['startDataDate']}")
                if end_date:
                    params['endDataDate'] = end_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置结束日期: {params['endDataDate']}")
                
                # 调用API获取数据
                success, response = client.get_sb_creatives(**params)
                
                # 增加延迟，确保符合每1秒1次的限流规则
                import time
                time.sleep(1.1)  # 增加1.1秒延迟，确保不超过限流
                
                if not success:
                    error_msg = f"获取市场 {market_id} 的SB广告创意数据失败: {response.get('error', '未知错误')}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 提取数据
                creative_data_list = response.get('data', [])
                next_id = response.get('next_id')
                has_more = response.get('has_more', False)
                
                logger.info(f"获取到 {len(creative_data_list)} 条SB广告创意数据，next_id: {next_id}, has_more: {has_more}")
                
                if not creative_data_list:
                    logger.info(f"市场 {market_id} 的第 {page_num} 页没有数据")
                    page_num += 1
                    continue
                
                # 处理每一条创意数据
                for creative_data in creative_data_list:
                    try:
                        # 映射数据
                        mapped_data = map_sb_creative_data(creative_data)
                        
                        # 创建或更新AdsSbCreative对象
                        ads_sb_creative, created = AdsSbCreative.objects.update_or_create(
                            market_id=mapped_data['market_id'],
                            create_date=mapped_data['create_date'],
                            # portfolio_id=mapped_data['portfolio_id'],
                            campaign_id=mapped_data['campaign_id'],
                            group_id=mapped_data.get('group_id'),
                            ad_id=mapped_data['ad_id'],
                            ads_type=mapped_data.get('ads_type'),
                            creative_type=mapped_data.get('creative_type'),
                            asins=mapped_data.get('asins'),
                            defaults=mapped_data
                        )
                        
                        if created:
                            logger.debug(f"创建新的SB广告创意记录: {mapped_data['ad_name'] or mapped_data['ad_id']}")
                        else:
                            logger.debug(f"更新SB广告创意记录: {mapped_data['ad_name'] or mapped_data['ad_id']}")
                        
                        success_count += 1
                        total_processed_for_market += 1
                        
                    except Exception as e:
                        error_msg = f"处理SB广告创意数据失败: {str(e)}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                
                page_num += 1
                
            logger.info(f"市场ID {market_id} 的SB广告创意数据处理完成，共处理 {total_processed_for_market} 条数据")
        
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = success_count + failed_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        logger.info(f"SB广告创意数据同步完成，总处理 {sync_log.total_count} 条，成功 {sync_log.success_count} 条，失败 {sync_log.failed_count} 条")
        
        return Response({
            'success': True,
            'message': 'SB广告创意数据同步成功',
            'data': {
                'total_count': sync_log.total_count,
                'success_count': sync_log.success_count,
                'failed_count': sync_log.failed_count
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # 更新同步日志状态为失败
        sync_log.status = 'failed'
        sync_log.failed_count += 1
        sync_log.detailed_error = str(e)
        sync_log.save()
        
        logger.error(f"同步SB广告创意数据时发生异常: {str(e)}")
        
        return Response({
            'success': False,
            'message': f'同步失败: {str(e)}',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 映射SB广告目标投放数据到模型格式
def map_sb_targeting_data(data):
    """
    映射SB广告目标投放数据到模型格式
    Args:
        data: 原始数据
    
    Returns:
        dict: 映射后的数据
    """
    # 数据清洗和类型转换
    mapped_data = {
        'market_id': int(data.get('marketId', 0)),
        'portfolio_id': data.get('portfolioId', ''),
        'portfolio_name': data.get('portfolioName', ''),
        'campaign_id': data.get('campaignId', ''),
        'campaign_name': data.get('campaignName', ''),
        'group_id': data.get('groupId', ''),
        'group_name': data.get('groupName', ''),
        'targeting_id': data.get('targetingId', ''),
        'bid': float(data.get('bid', 0.0)),
        'ads_type': data.get('adsType', ''),
        'state': data.get('state', ''),
        'impressions': int(data.get('impressions', 0)),
        'clicks': int(data.get('clicks', 0)),
        'cost': float(data.get('cost', 0.0)),
        'ads_orders': int(data.get('adsOrders', 0)),
        'ads_sales': float(data.get('adsSales', 0.0)),
        'ads_product_orders': int(data.get('adsProductOrders', 0)),
        'ads_product_sales': float(data.get('adsProductSales', 0.0)),
        'other_product_sales': float(data.get('otherProductSales', 0.0)),
        'view_impressions': int(data.get('viewImpressions', 0)),
        'new_buyer_orders': int(data.get('newBuyerOrders', 0)),
        'new_buyer_sales': float(data.get('newBuyerSales', 0.0)),
        'page_views': int(data.get('pageViews', 0)),
        'create_date': data.get('createDate', ''),
    }
    
    return mapped_data


# 从Gerpgo同步SB广告目标投放数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sb_targeting_data_from_gerpgo(request):
    """
    从Gerpgo同步SB广告目标投放数据
    """
    logger = logging.getLogger(__name__)
    
    # 验证请求数据
    serializer = SBTargetingDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SBTargeting数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # 获取请求参数
    market_ids = serializer.validated_data.get('marketIds', [])
    count = serializer.validated_data.get('count', 100)
    next_id = serializer.validated_data.get('nextId')
    start_data_date = serializer.validated_data.get('startDataDate')
    end_data_date = serializer.validated_data.get('endDataDate')

    # 如果没有日期参数，默认使用近14天
    if not start_data_date and not end_data_date:
        end_data_date = datetime.now()
        start_data_date = end_data_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_data_date.strftime('%Y-%m-%d')}，结束日期: {end_data_date.strftime('%Y-%m-%d')}")
    
    # 获取市场ID列表
    if not market_ids:
        # 如果没有指定市场ID，获取所有激活的市场
        markets = Market.objects.filter(is_active=True)
        market_ids = [market.id for market in markets]
    
    # 初始化Gerpgo客户端
    gerpgo_client = GerpgoAPIClient(
        appId=settings.GERPGO_APP_ID,
        appKey=settings.GERPGO_APP_KEY,
        base_url=settings.GERPGO_API_BASE_URL
    )
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sb_targeting_data',
        status='syncing',
        start_time=timezone.now(),
        total_count=0,
        success_count=0,
        failed_count=0
    )
    
    # 统计信息
    total_count = 0
    success_count = 0
    failed_count = 0
    error_messages = []
    
    try:
        # 遍历市场ID
        for market_id in market_ids:
            logger.info(f"开始同步市场 {market_id} 的SB广告目标投放数据")
            
            # 分页获取数据
            current_next_id = next_id
            while True:
                # 调用Gerpgo API获取数据
                success, result = gerpgo_client.get_sb_targetings(
                    market_ids=[market_id],
                    count=count,
                    next_id=current_next_id,
                    start_data_date=start_data_date,
                    end_data_date=end_data_date
                )
                
                if not success:
                    error_msg = f"获取市场 {market_id} 的SB广告目标投放数据失败: {result.get('error', '未知错误')}"
                    logger.error(error_msg)
                    error_messages.append(error_msg)
                    failed_count += 1
                    break
                
                # 获取数据
                targeting_data_list = result.get('data', [])
                current_next_id = result.get('next_id')
                
                logger.info(f"获取到市场 {market_id} 的SB广告目标投放数据 {len(targeting_data_list)} 条")
                
                # 处理数据
                for targeting_data in targeting_data_list:
                    total_count += 1
                    
                    
                        # 映射数据
                    mapped_data = map_sb_targeting_data(targeting_data)
                    
                    # 检查是否存在
                    try:
                        # 尝试使用targeting_id和market_id查找
                        ads_sb_targeting, created = AdsSbTargeting.objects.update_or_create(
                            targeting_id=mapped_data['targeting_id'],
                            market_id=mapped_data['market_id'],
                            create_date=mapped_data['create_date'],
                            # portfolio_id=mapped_data['portfolio_id'],
                            campaign_id=mapped_data['campaign_id'],
                            group_id=mapped_data['group_id'],
                            defaults=mapped_data
                        )
                        success_count += 1 
                    except Exception as e:
                        logger.error(f"处理SB广告目标投放数据失败: {str(e)}")
                        error_messages.append(f"处理数据失败: {str(e)}")
                        failed_count += 1
                
                # 检查是否还有下一页
                if not current_next_id:
                    break
        
        # 更新同步日志
        sync_log.status = 'success' if failed_count == 0 else 'partial_success'
        sync_log.total_count = total_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        sync_log.end_time = timezone.now()
        sync_log.sync_message = '\n'.join(error_messages[:10])  # 只保存前10条错误信息
        sync_log.save()
        
        # 返回响应
        return Response({
            'status': 'success',
            'message': f'同步完成，共 {total_count} 条数据，成功 {success_count} 条，失败 {failed_count} 条',
            'total_count': total_count,
            'success_count': success_count,
            'failed_count': failed_count
        })
    
    except Exception as e:
        logger.error(f"同步SB广告目标投放数据异常: {str(e)}")
        
        # 更新同步日志
        sync_log.status = 'failed'
        sync_log.total_count = total_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        sync_log.end_time = timezone.now()
        sync_log.sync_message = str(e)
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'同步过程中发生错误: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 从Gerpgo获取SB广告目标投放数据
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
        # 处理market_ids参数
        if isinstance(market_ids, int):
            market_ids = [market_ids]
        
        # 构建请求参数
        request_params = {
            "marketIds": market_ids,
            "count": count,
        }
        
        # 添加可选参数
        if next_id is not None:
            request_params["nextId"] = next_id
        
        if start_data_date is not None:
            # 转换日期格式
            if isinstance(start_data_date, str):
                request_params["startDate"] = start_data_date
            else:
                request_params["startDate"] = start_data_date.strftime("%Y-%m-%d")
        
        if end_data_date is not None:
            # 转换日期格式
            if isinstance(end_data_date, str):
                request_params["endDate"] = end_data_date
            else:
                request_params["endDate"] = end_data_date.strftime("%Y-%m-%d")
        
        # 添加其他参数
        request_params.update(params)
        
        
        # 构建URL
        sb_targetings_url = f"{self.base_url.rstrip('/')}/operation/ads/adsSbTargeting/query"
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "accessToken": self.access_token,
        }
        
        # 重试逻辑
        max_retries = 3
        retry_interval = 1
        
        for retry in range(max_retries):
            try:
                # 发送请求
                response = self._session.post(
                    sb_targetings_url,
                    json=request_params,
                    headers=headers,
                    timeout=self.timeout,
                )
                
                # 检查响应状态
                if response.status_code == 200:
                    data = response.json()
                    # 检查是否有next_id
                    next_id = data.get("nextId")
                    # 构造结果
                    result = {
                        "data": data.get("data", []),
                        "next_id": next_id
                    }
                    return True, result
                elif response.status_code in [429, 509]:
                    # 限流处理，等待后重试
                    time.sleep(1)
                    continue
                else:
                    # 其他错误
                    return False, {"error": f"请求失败: {response.status_code}", "message": response.text}
            
            except RequestException as e:
                # 网络错误，使用指数退避策略重试
                wait_time = retry_interval * (2 ** retry)
                logger.error(f"获取SB广告目标投放数据失败，正在重试 ({retry + 1}/{max_retries}): {str(e)}")
                time.sleep(wait_time)
                continue
        
        # 重试次数用完
        return False, {"error": "重试次数用完，获取数据失败"}
    
    except Exception as e:
        logger.error(f"获取SB广告目标投放数据异常: {str(e)}")
        return False, {"error": str(e)}


# 添加map_sb_placement_data函数
def map_sb_placement_data(placement_data):
    """将Gerpgo返回的SB广告展示位置数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': placement_data.get('marketId'),
        'portfolio_id': placement_data.get('portfolioId'),
        'portfolio_name': placement_data.get('portfolioName'),
        'campaign_id': placement_data.get('campaignId'),
        'campaign_name': placement_data.get('campaignName'),
        'placement': placement_data.get('placement'),
        'targeting_type': placement_data.get('targetingType'),
        'ads_type': placement_data.get('adsType'),
        'budget_type': placement_data.get('budgetType'),
        'budget': placement_data.get('budget'),
        'asins': placement_data.get('asins'),
        'state': placement_data.get('state'),
        'serving_status': placement_data.get('servingStatus'),
        'start_date': placement_data.get('startDate'),
        'end_date': placement_data.get('endDate'),
        'create_date': placement_data.get('createDate'),
        'impressions': placement_data.get('impressions'),
        'clicks': placement_data.get('clicks'),
        'cost': placement_data.get('cost'),
        'ads_orders': placement_data.get('adsOrders'),
        'ads_sales': placement_data.get('adsSales'),
        'ads_product_orders': placement_data.get('adsProductOrders'),
        'ads_product_sales': placement_data.get('adsProductSales'),
        'other_product_sales': placement_data.get('otherProductSales'),
        'view_impressions': placement_data.get('viewImpressions'),
        'new_buyer_orders': placement_data.get('newBuyerOrders'),
        'new_buyer_sales': placement_data.get('newBuyerSales'),
        'page_views': placement_data.get('pageViews'),
    }

# 添加sync_sb_placement_data_from_gerpgo视图函数
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sb_placement_data_from_gerpgo(request):
    """从Gerpgo同步SB广告展示位置数据"""
    # 验证请求数据
    serializer = SBPlacementDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SBPlacement数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    start_date = data.get('startDataDate')
    end_date = data.get('endDataDate')

    # 如果没有日期参数，默认使用近14天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sb_placement_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SB广告展示位置数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SBPlacement数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SB广告展示位置数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 分页获取所有数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的第 {page_num} 页数据")
                
                # 构建请求参数
                params = {
                    'marketId': market_id,
                    'count': count
                }
                
                # 添加nextId参数
                if next_id is not None:
                    params['nextId'] = next_id
                    logger.debug(f"当前分页参数 - nextId: {next_id}")
                
                if start_date:
                    params['startDataDate'] = start_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置开始日期: {params['startDataDate']}")
                if end_date:
                    params['endDataDate'] = end_date.strftime('%Y-%m-%d')
                    logger.debug(f"设置结束日期: {params['endDataDate']}")
                
                # 调用API获取数据
                success, response = client.get_sb_placement(**params)
                
                # 增加延迟，确保符合每1秒1次的限流规则
                import time
                time.sleep(1.1)  # 增加1.1秒延迟，确保不超过限流
                
                if not success:
                    error_msg = f"获取市场 {market_id} 的SB广告展示位置数据失败: {response.get('error', '未知错误')}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 提取数据
                placement_data_list = response.get('data', [])
                next_id = response.get('next_id')
                has_more = response.get('has_more', False)
                
                logger.info(f"获取到 {len(placement_data_list)} 条SB广告展示位置数据，next_id: {next_id}, has_more: {has_more}")
                
                if not placement_data_list:
                    logger.info(f"市场 {market_id} 的第 {page_num} 页没有数据")
                    page_num += 1
                    continue
                
                # 处理每一条展示位置数据
                for placement_data in placement_data_list:
                    try:
                        # 映射数据
                        mapped_data = map_sb_placement_data(placement_data)
                        
                        # 创建或更新AdsSbPlacement对象
                        ads_sb_placement, created = AdsSbPlacement.objects.update_or_create(
                            market_id=mapped_data['market_id'],  # 确保关联到正确的市场ID
                            create_date=mapped_data['create_date'],  # 使用当前日期作为报告日期
                            # portfolio_id=mapped_data['portfolio_id'],  # 确保关联到正确的组合ID
                            campaign_id=mapped_data['campaign_id'],  # 确保关联到正确的广告组ID
                            placement=mapped_data['placement'],  # 确保关联到正确的展示位置
                            defaults=mapped_data
                        )
                        
                        if created:
                            logger.debug(f"创建新的SB广告展示位置记录: {mapped_data.get('campaign_name', 'N/A')}")
                        else:
                            logger.debug(f"更新SB广告展示位置记录: {mapped_data.get('campaign_name', 'N/A')}")
                        
                        success_count += 1
                        total_processed_for_market += 1
                        
                    except Exception as e:
                        error_msg = f"处理SB广告展示位置数据失败: {str(e)}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                
                page_num += 1
                
            logger.info(f"市场ID {market_id} 的SB广告展示位置数据处理完成，共处理 {total_processed_for_market} 条数据")
        
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = success_count + failed_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        logger.info(f"SB广告展示位置数据同步完成，总处理 {sync_log.total_count} 条，成功 {sync_log.success_count} 条，失败 {sync_log.failed_count} 条")
        
        return Response({
            'success': True,
            'message': 'SB广告展示位置数据同步成功',
            'data': {
                'total_count': sync_log.total_count,
                'success_count': sync_log.success_count,
                'failed_count': sync_log.failed_count
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # 更新同步日志状态为失败
        sync_log.status = 'failed'
        sync_log.detailed_error = str(e)
        sync_log.save()
        
        logger.error(f"同步SB广告展示位置数据时发生异常: {str(e)}")
        return Response({
            'success': False,
            'message': f'同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# SB搜索词数据映射函数
def map_sb_search_terms_data(search_term_data):
    """将Gerpgo返回的SB广告搜索词数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': search_term_data.get('marketId'),
        'portfolio_id': search_term_data.get('portfolioId'),
        'portfolio_name': search_term_data.get('portfolioName'),
        'campaign_id': search_term_data.get('campaignId'),
        'campaign_name': search_term_data.get('campaignName'),
        'group_id': search_term_data.get('groupId'),
        'group_name': search_term_data.get('groupName'),
        'keyword_id': search_term_data.get('keywordId'),
        'keyword_text': search_term_data.get('keywordText'),
        'query': search_term_data.get('query'),
        'match_type': search_term_data.get('matchType'),
        'impressions': search_term_data.get('impressions'),
        'clicks': search_term_data.get('clicks'),
        'cost': search_term_data.get('cost'),
        'ads_orders': search_term_data.get('adsOrders'),
        'ads_sales': search_term_data.get('adsSales'),
        'view_impressions': search_term_data.get('viewImpressions'),
        'create_date': search_term_data.get('createDate'),
    }

# 同步SB广告搜索词数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sb_search_terms_data_from_gerpgo(request):
    """从Gerpgo同步SB广告搜索词数据"""
    # 验证请求数据
    serializer = SBSearchTermsDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SBSearchTerms数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    start_date = data.get('startDataDate')
    end_date = data.get('endDataDate')

    # 如果没有日期参数，默认使用近14天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sb_search_terms_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SB广告搜索词数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SBSearchTerms数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SB广告搜索词数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 循环获取分页数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的SB广告搜索词数据 - 第 {page_num} 页，next_id: {next_id}")
                
                # 调用API获取数据
                success, result = client.get_sb_search_terms(
                    market_ids=market_id,
                    count=count,
                    next_id=next_id,
                    start_data_date=start_date,
                    end_data_date=end_date
                )
                
                # 处理限流错误
                if not success and isinstance(result, dict) and result.get('status_code') == 429:
                    logger.warning(f"请求触发限流，等待2秒后重试")
                    time.sleep(2)  # 额外等待2秒后重试
                    continue
                
                # 处理其他错误
                if not success:
                    error_msg = f"获取市场ID {market_id} 的SB广告搜索词数据失败: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 检查结果格式
                if not isinstance(result, dict):
                    error_msg = f"获取市场ID {market_id} 的SB广告搜索词数据结果格式不正确: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 提取数据和分页信息
                search_term_data_list = result.get('data', [])
                next_id = result.get('next_id')
                has_more = result.get('has_more', False)
                
                logger.info(f"成功获取市场ID {market_id} 的SB广告搜索词数据 - 第 {page_num} 页，共 {len(search_term_data_list)} 条")
                
                # 处理每一条数据
                for search_term_data in search_term_data_list:
                    try:
                        # 映射数据格式
                        mapped_data = map_sb_search_terms_data(search_term_data)
                        
                        # 处理日期字段
                        if 'create_date' in mapped_data and mapped_data['create_date']:
                            mapped_data['create_date'] = datetime.strptime(mapped_data['create_date'], '%Y-%m-%d').date()
                        if 'report_date' in mapped_data and mapped_data['report_date']:
                            if isinstance(mapped_data['report_date'], str):
                                mapped_data['report_date'] = datetime.strptime(mapped_data['report_date'], '%Y-%m-%d').date()
                        
                        # 准备更新或创建数据的关键字
                        update_fields = [field for field in mapped_data.keys() if field not in ['market_id', 'id', 'report_date', 'hash']]
                        
                        # 使用update_or_create避免重复数据
                        obj, created = AdsSbSearchTerms.objects.update_or_create(
                            market_id=mapped_data['market_id'],
                            # portfolio_id=mapped_data['portfolio_id'],
                            campaign_id=mapped_data['campaign_id'],
                            group_id=mapped_data['group_id'],
                            keyword_id=mapped_data['keyword_id'],
                            match_type=mapped_data['match_type'],
                            query=mapped_data['query'],
                            create_date=mapped_data['create_date'],
                            defaults=mapped_data
                        )
                        
                        success_count += 1
                        total_processed_for_market += 1
                        
                    except Exception as e:
                        error_msg = f"处理市场ID {market_id} 的SB广告搜索词数据时发生错误: {str(e)}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                
                # 更新分页信息
                page_num += 1
                
                # 确保has_more的正确性
                if not search_term_data_list or len(search_term_data_list) < count:
                    has_more = False
                    logger.info(f"市场ID {market_id} 的SB广告搜索词数据已全部获取完毕，共处理 {total_processed_for_market} 条")
            
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = success_count + failed_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        logger.info(f"SB广告搜索词数据同步完成，总处理 {sync_log.total_count} 条，成功 {sync_log.success_count} 条，失败 {sync_log.failed_count} 条")
        
        return Response({
            'success': True,
            'message': 'SB广告搜索词数据同步成功',
            'data': {
                'total_count': sync_log.total_count,
                'success_count': sync_log.success_count,
                'failed_count': sync_log.failed_count
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SB广告搜索词数据同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        return Response({
            'success': False,
            'message': f'同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 添加前端数据接口
@api_view(['GET'])
@permission_classes([AllowAny])
def get_sb_search_terms_data(request):
    """获取SB广告搜索词数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        keyword_text = request.GET.get('keywordText')
        query = request.GET.get('query')
        campaign_id = request.GET.get('campaignId')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSbSearchTerms.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if keyword_text:
            queryset = queryset.filter(keyword_text__icontains=keyword_text)
        if query:
            queryset = queryset.filter(query__icontains=query)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for search_term in queryset:
            result.append({
                'id': search_term.id,
                'keywordId': search_term.keyword_id,
                'keywordText': search_term.keyword_text,
                'query': search_term.query,
                'marketId': search_term.market_id,
                'campaignId': search_term.campaign_id,
                'campaignName': search_term.campaign_name,
                'groupName': search_term.group_name,
                'matchType': search_term.match_type,
                'impressions': search_term.impressions,
                'clicks': search_term.clicks,
                'cost': float(search_term.cost),
                'adsSales': float(search_term.ads_sales),
                'ctr': float(search_term.ctr) if search_term.ctr else 0,
                'cpc': float(search_term.cpc) if search_term.cpc else 0,
                'acos': float(search_term.acos) if search_term.acos else 0,
                'roas': float(search_term.roas) if search_term.roas else 0,
                'reportDate': search_term.report_date.strftime('%Y-%m-%d'),
                'createDate': search_term.create_date.strftime('%Y-%m-%d') if search_term.create_date else None,
                'servingStatus': search_term.serving_status,
                'state': search_term.state
            })
        
        return Response({
            'success': True,
            'data': {
                'searchTerms': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取SB广告搜索词数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# SD广告活动数据映射函数
def map_sd_campaign_data(campaign_data):
    """将Gerpgo返回的SD广告活动数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': campaign_data.get('marketId'),
        'portfolio_id': campaign_data.get('portfolioId'),
        'portfolio_name': campaign_data.get('portfolioName'),
        'campaign_id': campaign_data.get('campaignId'),
        'campaign_name': campaign_data.get('campaignName'),
        'group_id': campaign_data.get('groupId'),
        'group_name': campaign_data.get('groupName'),
        'tactic': campaign_data.get('tactic'),
        'budget_type': campaign_data.get('budgetType'),
        'budget': campaign_data.get('budget'),
        'cost_type': campaign_data.get('costType'),
        'state': campaign_data.get('state'),
        'serving_status': campaign_data.get('servingStatus'),
        'start_date': campaign_data.get('startDate'),
        'end_date': campaign_data.get('endDate'),
        'create_date': campaign_data.get('createDate'),
        'impressions': campaign_data.get('impressions'),
        'clicks': campaign_data.get('clicks'),
        'cost': campaign_data.get('cost'),
        'ads_orders': campaign_data.get('adsOrders'),
        'ads_sales': campaign_data.get('adsSales'),
        'ads_product_orders': campaign_data.get('adsProductOrders'),
        'ads_product_sales': campaign_data.get('adsProductSales'),
        'other_product_sales': campaign_data.get('otherProductSales'),
        'view_impressions': campaign_data.get('viewImpressions'),
        'new_buyer_orders': campaign_data.get('newBuyerOrders'),
        'new_buyer_sales': campaign_data.get('newBuyerSales'),
        'page_views': campaign_data.get('pageViews')
    }


# 同步SD广告活动数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sd_campaign_data_from_gerpgo(request):
    """从Gerpgo同步SD广告活动数据"""
    # 验证请求数据
    serializer = SDSCampaignDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SDSCampaign数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    start_date = data.get('startDataDate')
    end_date = data.get('endDataDate')

    # 如果没有日期参数，默认使用近14天
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sd_campaign_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SD广告活动数据，批次ID: {sync_log.id}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 同步SDCampaign数据
        success_count = 0
        failed_count = 0
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 为每个市场ID获取数据
        for market_id in market_ids:
            logger.info(f"获取市场ID {market_id} 的SD广告活动数据")
            
            # 初始化分页参数
            next_id = None
            has_more = True
            page_num = 1
            total_processed_for_market = 0
            
            # 循环获取分页数据
            while has_more:
                logger.info(f"获取市场ID {market_id} 的SD广告活动数据 - 第 {page_num} 页，next_id: {next_id}")
                
                # 调用API获取数据
                # 构建请求参数
                api_params = {
                    'marketIds': [market_id],
                    'count': count
                }
                if next_id:
                    api_params['nextId'] = next_id
                if start_date:
                    api_params['startDataDate'] = start_date.strftime('%Y-%m-%d')
                if end_date:
                    api_params['endDataDate'] = end_date.strftime('%Y-%m-%d')
                
                # 调用专门的get_sd_campaigns方法
                success, result = client.get_sd_campaign(
                    market_ids=[market_id],
                    count=count,
                    next_id=next_id,
                    start_data_date=start_date,
                    end_data_date=end_date
                )
                
                # 处理限流错误
                if not success and isinstance(result, dict) and result.get('status_code') == 429:
                    logger.warning(f"请求触发限流，等待2秒后重试")
                    time.sleep(2)  # 额外等待2秒后重试
                    continue
                
                # 处理其他错误
                if not success:
                    error_msg = f"获取市场ID {market_id} 的SD广告活动数据失败: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 检查结果格式
                if not isinstance(result, dict):
                    error_msg = f"获取市场ID {market_id} 的SD广告活动数据结果格式不正确: {result}"
                    logger.error(error_msg)
                    detailed_errors.append(error_msg)
                    failed_count += 1
                    break
                
                # 提取数据和分页信息
                campaign_data_list = result.get('data', [])
                next_id = result.get('next_id')
                has_more = result.get('has_more', False)
                
                logger.info(f"成功获取市场ID {market_id} 的SD广告活动数据 - 第 {page_num} 页，共 {len(campaign_data_list)} 条")
                
                # 处理每一条数据
                for campaign_data in campaign_data_list:
                    try:
                        # 映射数据格式
                        mapped_data = map_sd_campaign_data(campaign_data)
                        
                        # 处理日期字段
                        date_fields = ['create_date', 'start_date', 'end_date', 'report_date']
                        for field in date_fields:
                            if field in mapped_data and mapped_data[field]:
                                if isinstance(mapped_data[field], str):
                                    mapped_data[field] = datetime.strptime(mapped_data[field], '%Y-%m-%d').date()
                        
                        # 准备更新或创建数据的关键字
                        update_fields = [field for field in mapped_data.keys() if field not in ['market_id', 'id', 'report_date', 'hash']]
                        
                        # 使用update_or_create避免重复数据
                        obj, created = AdsSdCampaign.objects.update_or_create(
                            market_id=mapped_data['market_id'],
                            # portfolio_id=mapped_data['portfolio_id'],
                            campaign_id=mapped_data['campaign_id'],
                            group_id=mapped_data['group_id'],
                            create_date=mapped_data['create_date'],
                            defaults=mapped_data
                        )
                        
                        success_count += 1
                        total_processed_for_market += 1
                        
                    except Exception as e:
                        error_msg = f"处理市场ID {market_id} 的SD广告活动数据时发生错误: {str(e)}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        failed_count += 1
                        continue
                
                # 更新分页信息
                page_num += 1
                
                # 确保has_more的正确性
                if not campaign_data_list or len(campaign_data_list) < count:
                    has_more = False
                    logger.info(f"市场ID {market_id} 的SD广告活动数据已全部获取完毕，共处理 {total_processed_for_market} 条")
            
        # 更新同步日志
        sync_log.status = 'success'
        sync_log.total_count = success_count + failed_count
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        logger.info(f"SD广告活动数据同步完成，总处理 {sync_log.total_count} 条，成功 {sync_log.success_count} 条，失败 {sync_log.failed_count} 条")
        
        return Response({
            'success': True,
            'message': 'SD广告活动数据同步成功',
            'data': {
                'total_count': sync_log.total_count,
                'success_count': sync_log.success_count,
                'failed_count': sync_log.failed_count
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SD广告活动数据同步过程发生异常: {str(e)}", exc_info=True)
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        if detailed_errors:
            sync_log.detailed_error = '\n'.join(detailed_errors[:10])  # 只保存前10个错误
        sync_log.save()
        
        return Response({
            'success': False,
            'message': f'同步失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# SDProduct数据映射函数
def map_sd_product_data(product_data):
    """将Gerpgo返回的SD广告产品数据映射为统一格式"""
    # 从API返回的数据结构中提取所需字段并映射到模型字段
    return {
        'market_id': product_data.get('marketId'),
        'portfolio_id': product_data.get('portfolioId'),
        'portfolio_name': product_data.get('portfolioName'),
        'campaign_id': product_data.get('campaignId'),
        'campaign_name': product_data.get('campaignName'),
        'group_id': product_data.get('groupId'),
        'group_name': product_data.get('groupName'),
        'create_date': product_data.get('createDate'),
        'ad_id': product_data.get('adId'),
        'msku': product_data.get('msku'),
        'asin': product_data.get('asin'),
        'cost_type': product_data.get('costType'),
        'state': product_data.get('state'),
        'serving_status': product_data.get('servingStatus'),
        'impressions': product_data.get('impressions'),
        'clicks': product_data.get('clicks'),
        'cost': product_data.get('cost'),
        'ads_orders': product_data.get('adsOrders'),
        'ads_sales': product_data.get('adsSales'),
        'ads_product_orders': product_data.get('adsProductOrders'),
        'ads_product_sales': product_data.get('adsProductSales'),
        'other_product_sales': product_data.get('otherProductSales'),
        'view_impressions': product_data.get('viewImpressions'),
        'new_buyer_orders': product_data.get('newBuyerOrders'),
        'new_buyer_sales': product_data.get('newBuyerSales'),
        'page_views': product_data.get('pageViews'),
    }


# SDProduct数据同步视图
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_sd_product_data_from_gerpgo(request):
    """
    从Gerpgo同步SD广告产品数据
    根据传入的开始日期和结束日期，按天循环取数并将日期存入数据库
    :param request: 请求对象，包含同步参数(marketIds, startDataDate, endDataDate等)
    :return: 响应对象，包含同步结果
    """
    # 验证请求数据
    serializer = SDProductDataRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"SDProduct数据请求验证失败: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_market_ids = data.get('marketIds')
    # 如果请求中提供了marketIds且不为空，则使用请求中的marketIds
    if request_market_ids and isinstance(request_market_ids, list) and request_market_ids:
        market_ids = request_market_ids
        logger.info(f"使用请求中提供的市场ID列表: {market_ids}")
    else:
        # 否则从本地Market表中获取所有可用的market_id
        logger.info("请求中未提供有效的市场ID列表，从数据库中获取")
        try:
            # 获取所有同步成功的市场ID
            market_objects = Market.objects.filter(sync_status='success')
            market_ids = list(market_objects.values_list('market_id', flat=True))
            logger.info(f"从数据库中获取到 {len(market_ids)} 个市场ID")
        except Exception as e:
            logger.error(f"从数据库获取市场ID失败: {str(e)}")
            raise ValueError("无法获取市场ID列表，请先同步店铺信息")
    count = data.get('count', 100)
    start_date = data.get('startDataDate')
    end_date = data.get('endDataDate')

    # 如果没有日期参数，默认使用近14天
    if not start_date and not end_date:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=14)
        logger.info(f"未提供日期参数，默认使用近14天数据，开始日期: {start_date.strftime('%Y-%m-%d')}，结束日期: {end_date.strftime('%Y-%m-%d')}")
    
    # 确保日期是date类型
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()
    
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='sd_product_data',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"开始同步SD广告产品数据，批次ID: {sync_log.id}，日期范围: {start_date} 至 {end_date}")
    
    # 用于存储详细错误信息
    detailed_errors = []
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        logger.info(f"API客户端初始化成功")
        
        # 初始化计数器
        total_success_count = 0
        total_error_count = 0
        day_results = []  # 记录每天的同步结果
        
        # 确保market_ids是列表类型且不为空
        if not isinstance(market_ids, list) or not market_ids:
            logger.warning(f"市场ID列表为空或格式不正确: {market_ids}")
            raise ValueError("市场ID列表不能为空")
        
        # 按天循环取数
        current_date = start_date
        while current_date <= end_date:
            logger.info(f"开始同步日期：{current_date}")
            day_success_count = 0
            day_error_count = 0
            
            # 为每个市场ID获取当天数据
            for market_id in market_ids:
                logger.info(f"获取市场ID {market_id} 日期 {current_date} 的SD广告产品数据")
                
                # 初始化分页参数
                next_id = None
                has_more = True
                page_num = 1
                
                # 分页获取当天所有数据
                while has_more:
                    logger.info(f"获取市场ID {market_id} 日期 {current_date} 的第 {page_num} 页数据")
                    
                    # 调用API获取数据，开始和结束日期都设为当前日期，确保只查询单天数据
                    success, response = client.get_sd_product(
                        market_ids=[market_id],
                        count=count,
                        next_id=next_id,
                        start_data_date=current_date,  # 开始日期设为当前日期
                        end_data_date=current_date     # 结束日期也设为当前日期，确保只查询单天数据
                    )
                    
                    # 增加延迟，确保符合每1秒1次的限流规则
                    import time
                    time.sleep(1.1)  # 增加1.1秒延迟，确保不超过限流
                    
                    if not success:
                        error_msg = f"获取市场 {market_id} 日期 {current_date} 的SD广告产品数据失败: {response.get('error', '未知错误')}"
                        logger.error(error_msg)
                        detailed_errors.append(error_msg)
                        day_error_count += 1
                        break
                    
                    # 提取数据
                    product_data_list = response.get('data', [])
                    next_id = response.get('next_id')
                    has_more = response.get('has_more', False)
                    
                    logger.info(f"获取到 {len(product_data_list)} 条SD广告产品数据，nextId: {next_id}, hasMore: {has_more}")
                    
                    if not product_data_list:
                        logger.info(f"市场 {market_id} 日期 {current_date} 的第 {page_num} 页没有数据")
                        break
                    
                    # 处理每一条产品数据
                    for product_data in product_data_list:
                        try:
                            # 映射数据
                            mapped_data = map_sd_product_data(product_data)
                            
                            # 处理日期字段
                            if 'create_date' in mapped_data and mapped_data['create_date']:
                                if isinstance(mapped_data['create_date'], str):
                                    mapped_data['create_date'] = datetime.strptime(mapped_data['create_date'], '%Y-%m-%d').date()
                            
                            # 创建或更新AdsSdProduct对象
                            ads_sd_product, created = AdsSdProduct.objects.update_or_create(
                                # portfolio_id=mapped_data['portfolio_id'],
                                campaign_id=mapped_data['campaign_id'],
                                ad_id=mapped_data['ad_id'],
                                market_id=mapped_data['market_id'], 
                                group_id=mapped_data.get('group_id'),
                                msku=mapped_data.get('msku'),
                                asin=mapped_data.get('asin'),
                                create_date=mapped_data.get('create_date'),
                                defaults=mapped_data
                            )
                            
                            if created:
                                logger.debug(f"创建新的SD广告产品记录: 日期{current_date}-{mapped_data.get('msku', 'Unknown')}")
                            else:
                                logger.debug(f"更新SD广告产品记录: 日期{current_date}-{mapped_data.get('msku', 'Unknown')}")
                            
                            day_success_count += 1
                            
                        except Exception as e:
                            error_msg = f"处理日期{current_date}SD广告产品数据异常: {str(e)}"
                            logger.error(error_msg)
                            detailed_errors.append(error_msg)
                            day_error_count += 1
                            continue
                    
                    page_num += 1
            
            # 记录当天的同步结果
            day_results.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'success_count': day_success_count,
                'error_count': day_error_count
            })
            total_success_count += day_success_count
            total_error_count += day_error_count
            logger.info(f"日期{current_date}同步完成，成功：{day_success_count}，失败：{day_error_count}")
            
            # 移动到下一天
            current_date = current_date + timedelta(days=1)
        
        # 更新同步日志
        sync_log.status = 'success' if total_error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = total_success_count
        sync_log.failed_count = total_error_count
        sync_log.total_count = total_success_count + total_error_count
        sync_log.error_message = json.dumps({
            'error_details': detailed_errors,
            'day_results': day_results,  # 记录每天的同步结果
            'total_processed': total_success_count + total_error_count
        }, ensure_ascii=False)  # 记录错误详情
        sync_log.save()
        
        logger.info(f"SD广告产品数据同步完成，批次ID: {sync_log.id}，总处理 {sync_log.total_count} 条，成功 {sync_log.success_count} 条，失败 {sync_log.failed_count} 条")
        
        # 返回成功响应
        return Response({
            'status': 'success',
            'message': f'数据同步完成，共同步{len(day_results)}天数据',
            'sync_log_id': sync_log.id,
            'date_range': f'{start_date} 至 {end_date}',
            'total_processed': total_success_count + total_error_count,
            'success_count': total_success_count,
            'failed_count': total_error_count,
            'day_results': day_results  # 返回每天的详细结果
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"SD广告产品数据同步过程中发生异常：{str(e)}")  # 记录错误信息

        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.error_message = json.dumps({
            'error_details': [str(e)],
            'total_processed': 0
        }, ensure_ascii=False)  # 记录异常信息
        sync_log.save()  # 保存同步日志到数据库

        # 返回失败响应
        return Response({
            'status': 'failed',
            'message': 'SD广告产品数据同步过程中发生异常',
            'sync_log_id': sync_log.id,
            'error_details': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 获取SDProduct数据视图
@api_view(['GET'])
@permission_classes([AllowAny])
def get_sd_product_data(request):
    """获取SD广告产品数据 - 前端数据接口"""
    try:
        # 获取请求参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('pageSize', 100))
        market_id = request.GET.get('marketId')
        asin = request.GET.get('asin')
        title = request.GET.get('title')
        campaign_id = request.GET.get('campaignId')
        start_date = request.GET.get('startDate')
        end_date = request.GET.get('endDate')
        
        # 构建查询
        queryset = AdsSdProduct.objects.all()
        
        # 应用过滤条件
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        if asin:
            queryset = queryset.filter(asin__icontains=asin)
        if title:
            queryset = queryset.filter(title__icontains=title)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
        
        # 计算总数
        total = queryset.count()
        
        # 应用分页
        queryset = queryset.order_by('-report_date')[(page-1)*page_size:page*page_size]
        
        # 格式化结果
        result = []
        for product in queryset:
            result.append({
                'id': product.id,
                'productId': product.product_id,
                'asin': product.asin,
                # 'title': product.title,
                # 'sku': product.sku,
                'marketId': product.market_id,
                'campaignId': product.campaign_id,
                'campaignName': product.campaign_name,
                'groupName': product.group_name,
                'impressions': product.impressions,
                'clicks': product.clicks,
                'cost': float(product.cost),
                'adsSales': float(product.ads_sales),
                'ctr': float(product.ctr) if product.ctr else 0,
                'cpc': float(product.cpc) if product.cpc else 0,
                'acos': float(product.acos) if product.acos else 0,
                'roas': float(product.roas) if product.roas else 0,
                'reportDate': product.report_date.strftime('%Y-%m-%d') if product.report_date else None,
                'createDate': product.create_date.strftime('%Y-%m-%d') if product.create_date else None,
                'state': product.state,
                # 'adsType': product.ads_type
            })
        
        return Response({
            'success': True,
            'data': {
                'products': result,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f"获取SD广告产品数据异常: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# 映射库存分类账数据
def map_inventory_storage_ledger_data(raw_data):
    """映射库存分类账数据"""
    mapped_data = {}
    
    # 映射必要字段
    mapped_data['warehouse_name'] = raw_data.get('warehouseName')
    mapped_data['warehouse_id'] = raw_data.get('warehouseId')
    mapped_data['report_date'] = raw_data.get('reportDate')
    mapped_data['sku_name'] = raw_data.get('skuName')
    mapped_data['sku'] = raw_data.get('sku')
    mapped_data['fnsku'] = raw_data.get('fnsku')
    mapped_data['msku'] = raw_data.get('msku')
    mapped_data['source_msku'] = raw_data.get('sourceMSKU')
    mapped_data['asin'] = raw_data.get('asin')
    mapped_data['disposition'] = raw_data.get('disposition')
    mapped_data['starting_warehouse_balance'] = raw_data.get('startingWarehouseBalance')
    mapped_data['ending_warehouse_balance'] = raw_data.get('endingWarehouseBalance')
    mapped_data['warehouse_transfer_in_and_out'] = raw_data.get('warehouseTransferInAndOut')
    mapped_data['in_transit_between_warehouses'] = raw_data.get('inTransitBetweenWarehouses')
    mapped_data['receipts'] = raw_data.get('receipts')
    mapped_data['customer_shipments'] = raw_data.get('customerShipments')
    mapped_data['customer_returns'] = raw_data.get('customerReturns')
    mapped_data['vendor_returns'] = raw_data.get('vendorReturns')
    mapped_data['found'] = raw_data.get('found')
    mapped_data['lost'] = raw_data.get('lost')
    mapped_data['damaged'] = raw_data.get('damaged')
    mapped_data['disposed'] = raw_data.get('disposed')
    mapped_data['other_events'] = raw_data.get('otherEvents')
    mapped_data['unknown_events'] = raw_data.get('unknownEvents')
    mapped_data['country'] = raw_data.get('country')
    mapped_data['create_time'] = raw_data.get('createTime')
    mapped_data['update_time'] = raw_data.get('updateTime')

    return mapped_data


# 同步库存分类账数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_inventory_storage_ledger_from_gerpgo(request):
    """同步库存分类账数据"""
    logger = logging.getLogger(__name__)
    
    # 验证请求参数
    serializer = InventoryStorageLedgerRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"同步库存分类账数据参数验证失败: {serializer.errors}")
        return Response({
            'success': False,
            'error': f"参数验证失败: {serializer.errors}"
        }, status=status.HTTP_400_BAD_REQUEST)


    # 创建同步日志前，处理日期对象序列化问题
    validated_data_copy = serializer.validated_data.copy()
    # 将date对象转换为字符串
    for key, value in validated_data_copy.items():
        if isinstance(value, date):
            validated_data_copy[key] = value.strftime('%Y-%m-%d')
        
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='inventory_storage_ledger',
        status='processing',
        # request_params=json.dumps(serializer.validated_data),
        start_time=timezone.now()
    )
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        
        # 获取分页参数
        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('pageSize', 100)
        
        # 格式化日期参数
        report_start_date = serializer.validated_data.get('reportStartDate')
        report_end_date = serializer.validated_data.get('reportEndDate')

        # 将date对象转换为字符串格式
        if isinstance(report_start_date, date):
            report_start_date = report_start_date.strftime('%Y-%m-%d')
        if isinstance(report_end_date, date):
            report_end_date = report_end_date.strftime('%Y-%m-%d')
 
        
        # 计算总页数
        total_pages = 1
        success_count = 0
        error_count = 0
        error_details = []
        
        while page <= total_pages:
            # 获取库存分类账数据
            success, data = client.get_inventory_storage_ledger(
                page=page,
                page_size=page_size,
                model = {
                    'reportStartDate': report_start_date,
                    'reportEndDate': report_end_date
                }
            )
            
            if not success:
                error_msg = f"获取第{page}页库存分类账数据失败: {data}"
                logger.error(error_msg)
                error_count += 1
                error_details.append(error_msg)
                break
            
            # 处理返回的数据
            if data and 'data' in data:
                total_pages = (data['data'].get('total', 0) + page_size - 1) // page_size
                
                # 处理每一条库存分类账数据
                for row in data['data'].get('rows', []):
                    try:
                        # 映射数据
                        mapped_data = map_inventory_storage_ledger_data(row)
                        
                        # 使用update_or_create来更新或创建数据
                        ledger, created = InventoryStorageLedger.objects.update_or_create(
                            source_msku=mapped_data['source_msku'],
                            fnsku=mapped_data['fnsku'],
                            country=mapped_data['country'],
                            warehouse_id=mapped_data['warehouse_name'],
                            disposition=mapped_data['disposition'],
                            report_date=mapped_data['report_date'],
                            defaults=mapped_data
                        )
                        
                        if created:
                            logger.info(f"创建库存分类账数据: {mapped_data['sku']} - {mapped_data['warehouse_id']} - {mapped_data['report_date']}")
                        else:
                            logger.info(f"更新库存分类账数据: {mapped_data['sku']} - {mapped_data['warehouse_id']} - {mapped_data['report_date']}")
                        
                        success_count += 1
                    except Exception as e:
                        error_msg = f"处理库存分类账数据异常: {str(e)}"
                        logger.error(error_msg)
                        error_count += 1
                        error_details.append(error_msg)
            else:
                break
            
            page += 1
        
        # 更新同步日志
        sync_log.status = 'success' if error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = success_count
        sync_log.error_count = error_count
        sync_log.response_message = json.dumps({
            'error_details': error_details,
            'total_processed': success_count + error_count
        })
        sync_log.save()
        
        # 返回成功响应
        return Response({
            'success': True,
            'message': f"库存分类账数据同步完成",
            'data': {
                'sync_log_id': sync_log.id,
                'success_count': success_count,
                'error_count': error_count,
                'total_processed': success_count + error_count
            }
        })
    
    except Exception as e:
        # 记录异常
        logger.error(f"同步库存分类账数据异常: {str(e)}")
        
        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.error_count = 1
        sync_log.response_message = str(e)
        sync_log.save()
        
        # 返回错误响应
        return Response({
            'success': False,
            'error': f"同步库存分类账数据失败: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 添加库存分类账明细数据映射函数
def map_inventory_storage_ledger_detail_data(raw_data):
    """映射库存分类账明细数据"""
    mapped_data = {}
    
    mapped_data['warehouse_name'] = raw_data.get('warehouseName')
    mapped_data['warehouse_id'] = raw_data.get('warehouseId')
    mapped_data['report_date'] = raw_data.get('reportDate')
    mapped_data['sku_name'] = raw_data.get('skuName')
    mapped_data['sku'] = raw_data.get('sku')
    mapped_data['fnsku'] = raw_data.get('fnsku')
    mapped_data['msku'] = raw_data.get('msku')
    mapped_data['source_msku'] = raw_data.get('sourceMSKU')
    mapped_data['asin'] = raw_data.get('asin')
    mapped_data['country'] = raw_data.get('country')
    mapped_data['disposition'] = raw_data.get('disposition')
    mapped_data['reference_id'] = raw_data.get('referenceId')
    mapped_data['quantity'] = raw_data.get('quantity')
    mapped_data['event_type'] = raw_data.get('eventType')
    mapped_data['fulfillment_center'] = raw_data.get('fulfillmentCenter')
    mapped_data['reason'] = raw_data.get('reason')
    mapped_data['reconciled_quantity'] = raw_data.get('reconciledQuantity')
    mapped_data['unreconciled_quantity'] = raw_data.get('unreconciledQuantity')
    mapped_data['create_time'] = raw_data.get('createTime')
    mapped_data['update_time'] = raw_data.get('updateTime')
    
    return mapped_data


# 在文件末尾添加同步库存分类账明细数据的视图函数
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_inventory_storage_ledger_detail(request):
    """同步库存分类账明细数据"""
    logger.info("开始同步库存分类账明细数据")
    
    # 验证请求参数
    serializer = InventoryStorageLedgerDetailRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"同步库存分类账明细数据参数验证失败: {serializer.errors}")
        return Response({
            'success': False,
            'error': f"参数验证失败: {serializer.errors}"
        }, status=status.HTTP_400_BAD_REQUEST)

    # 创建同步日志前，处理日期对象序列化问题
    validated_data_copy = serializer.validated_data.copy()
    # 将date对象转换为字符串
    for key, value in validated_data_copy.items():
        if isinstance(value, date):
            validated_data_copy[key] = value.strftime('%Y-%m-%d')
        
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='inventory_storage_ledger_detail',
        status='processing',
        start_time=timezone.now()
    )
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        
        # 获取分页参数
        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('pagesize', 100)
        
        # 格式化日期参数
        begin_report_date = serializer.validated_data.get('beginReportDate')
        end_report_date = serializer.validated_data.get('endReportDate')
        
        # 将date对象转换为字符串格式
        if isinstance(begin_report_date, date):
            begin_report_date = begin_report_date.strftime('%Y-%m-%d')
        if isinstance(end_report_date, date):
            end_report_date = end_report_date.strftime('%Y-%m-%d')
        
        # 计算总页数
        total_pages = 1
        success_count = 0
        error_count = 0
        error_details = []
        
        while page <= total_pages:
            # 获取库存分类账明细数据
            success, data = client.get_inventory_storage_ledger_detail(
                page=page,
                page_size=page_size,
                model={
                    'beginReportDate': begin_report_date,
                    'endReportDate': end_report_date
                }
            )
            
            if not success:
                error_msg = f"获取第{page}页库存分类账明细数据失败: {data}"
                logger.error(error_msg)
                error_count += 1
                error_details.append(error_msg)
                break
            
            # 处理返回的数据
            if data and 'data' in data:
                total_pages = (data['data'].get('total', 0) + page_size - 1) // page_size
                
                # 处理每一条库存分类账明细数据
                for row in data['data'].get('rows', []):
                    try:
                        # 映射数据
                        mapped_data = map_inventory_storage_ledger_detail_data(row)
                        
                        # 使用update_or_create来更新或创建数据
                        ledger_detail, created = InventoryStorageLedgerDetail.objects.update_or_create(
                            source_msku=mapped_data['source_msku'],
                            report_date=mapped_data['report_date'],
                            fnsku=mapped_data['fnsku'],
                            country=mapped_data['country'],
                            disposition=mapped_data['disposition'],
                            warehouse_name=mapped_data.get('warehouse_name'),
                            fulfillment_center=mapped_data.get('fulfillment_center'),
                            reference_id=mapped_data.get('reference_id'),
                            event_type=mapped_data['event_type'],
                            defaults=mapped_data
                        )
                        
                        if created:
                            logger.info(f"创建库存分类账明细数据: {mapped_data['sku']} - {mapped_data['event_type']}")
                        else:
                            logger.info(f"更新库存分类账明细数据: {mapped_data['sku']} - {mapped_data['event_type']}")
                        
                        success_count += 1
                    except Exception as e:
                        error_msg = f"处理库存分类账明细数据异常: {str(e)}"
                        logger.error(error_msg)
                        error_count += 1
                        error_details.append(error_msg)
            else:
                break
            
            page += 1
        
        # 更新同步日志
        sync_log.status = 'success' if error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = success_count
        sync_log.error_count = error_count
        sync_log.response_message = json.dumps({
            'error_details': error_details,
            'total_processed': success_count + error_count
        })
        sync_log.save()
        
        # 返回成功响应
        return Response({
            'success': True,
            'message': f"库存分类账明细数据同步完成",
            'data': {
                'sync_log_id': sync_log.id,
                'success_count': success_count,
                'error_count': error_count,
                'total_processed': success_count + error_count
            }
        })
    
    except Exception as e:
        # 记录异常
        logger.error(f"同步库存分类账明细数据异常: {str(e)}")
        
        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.error_count = 1
        sync_log.response_message = str(e)
        sync_log.save()
        
        # 返回错误响应
        return Response({
            'success': False,
            'error': f"同步库存分类账明细数据失败: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 数据映射函数：将API返回的交易数据映射到Transaction模型
def map_transaction_data(raw_data):
    """
    映射交易数据
    
    Args:
        raw_data: 原始API返回的交易数据
    
    Returns:
        dict: 映射后的Transaction模型数据
    """
    mapped_data = {}
    
    mapped_data['market_id'] = raw_data.get('marketId')
    mapped_data['market_name'] = raw_data.get('marketName')
    mapped_data['currency'] = raw_data.get('currency')
    mapped_data['currency_symbol'] = raw_data.get('currencySymbol')
    mapped_data['create_date'] = parse_date_string(raw_data.get('createDate'))
    mapped_data['standard_date'] = parse_date_string(raw_data.get('standardDate'))
    mapped_data['market_date'] = parse_date_string(raw_data.get('marketDate'))
    mapped_data['zero_date'] = parse_date_string(raw_data.get('zeroDate'))
    mapped_data['settlement_id'] = raw_data.get('settlementId')
    mapped_data['order_type'] = raw_data.get('orderType')
    mapped_data['type'] = raw_data.get('type')
    mapped_data['order_id'] = raw_data.get('orderId')
    mapped_data['sku'] = raw_data.get('sku')
    mapped_data['origin_sku'] = raw_data.get('originSku')
    mapped_data['description'] = raw_data.get('description')
    mapped_data['quantity'] = raw_data.get('quantity')
    mapped_data['market_place'] = raw_data.get('marketplace')
    mapped_data['fulfillment'] = raw_data.get('fulfillment')
    mapped_data['order_city'] = raw_data.get('orderCity')
    mapped_data['order_state'] = raw_data.get('orderState')
    mapped_data['order_postal'] = raw_data.get('orderPostal')
    mapped_data['tax_collection_model'] = raw_data.get('taxCollectionModel')
    mapped_data['product_sales'] = raw_data.get('productSales')
    mapped_data['product_sales_tax'] = raw_data.get('productSalesTax')
    mapped_data['shipping_credits'] = raw_data.get('shippingCredits')
    mapped_data['shipping_credits_tax'] = raw_data.get('shippingCreditsTax')
    mapped_data['gift_wrap_credits'] = raw_data.get('giftWrapCredits')
    mapped_data['gift_wrap_credits_tax'] = raw_data.get('giftWrapCreditsTax')
    mapped_data['regulatory_fees'] = raw_data.get('regulatoryFees')
    mapped_data['regulatory_fees_tax'] = raw_data.get('regulatoryFeesTax')
    mapped_data['promotional_rebates'] = raw_data.get('promotionalRebates')
    mapped_data['promotional_rebates_tax'] = raw_data.get('promotionalRebatesTax')
    mapped_data['points_granted'] = raw_data.get('pointsGranted')
    mapped_data['marketplace_withheld_tax'] = raw_data.get('marketplaceWithheldTax')
    mapped_data['selling_fees'] = raw_data.get('sellingFees')
    mapped_data['fba_fees'] = raw_data.get('fbaFees')
    mapped_data['other_transaction_fees'] = raw_data.get('otherTransactionFees')
    mapped_data['total'] = raw_data.get('total')
    mapped_data['update_date'] = raw_data.get('updateDate')
    mapped_data['country_code'] = raw_data.get('countryCode')
    
    return mapped_data

# 同步交易数据的视图函数
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_transaction(request):
    """同步交易数据"""
    logger.info("开始同步交易数据")
    logger.info(f"请求参数: {request.data}")
    
    # 验证请求参数
    serializer = TransactionRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"同步交易数据参数验证失败: {serializer.errors}")
        return Response({
            'success': False,
            'error': f"参数验证失败: {serializer.errors}"
        }, status=status.HTTP_400_BAD_REQUEST)

    # 创建同步日志前，处理日期对象序列化问题
    validated_data_copy = serializer.validated_data.copy()
    # 将date对象转换为字符串
    for key, value in validated_data_copy.items():
        if isinstance(value, date):
            validated_data_copy[key] = value.strftime('%Y-%m-%d')
        
    # 创建同步日志
    sync_log = SyncLog.objects.create(
        sync_type='transaction',
        status='processing',
        start_time=timezone.now()
    )
    
    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        
        # 获取分页参数
        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('pagesize', 100)
        
        # 格式化日期参数 - 同时支持下划线和驼峰命名格式
        purchase_start_date = serializer.validated_data.get('purchase_start_date') or serializer.validated_data.get('purchaseStartDate')
        purchase_end_date = serializer.validated_data.get('purchase_end_date') or serializer.validated_data.get('purchaseEndDate')
        query_date_type = serializer.validated_data.get('query_date_type') or serializer.validated_data.get('queryDateType', 0)
        
        # 记录日期参数详细日志
        logger.info(f"获取到的日期参数 - 开始日期: {purchase_start_date}, 结束日期: {purchase_end_date}, 查询日期类型: {query_date_type}")
        
        # 将date对象转换为字符串格式
        if isinstance(purchase_start_date, date):
            purchase_start_date = purchase_start_date.strftime('%Y-%m-%d')
            logger.info(f"转换后的开始日期: {purchase_start_date}")
        if isinstance(purchase_end_date, date):
            purchase_end_date = purchase_end_date.strftime('%Y-%m-%d')
            logger.info(f"转换后的结束日期: {purchase_end_date}")
        
        # 计算总页数
        total_pages = 1
        success_count = 0
        error_count = 0
        error_details = []

        # 根据时间范围删除旧数据（可选，如果需要完全替换数据）
        delete_old_data = serializer.validated_data.get('delete_old_data', False)
        if delete_old_data and purchase_start_date and purchase_end_date:
            try:
                # 将字符串转换回date对象用于查询
                from datetime import datetime
                start_dt = datetime.strptime(purchase_start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(purchase_end_date, '%Y-%m-%d').date()
                
                # 删除指定时间范围内的数据
                deleted_count, _ = Transaction.objects.filter(
                    market_date__date__range=[start_dt, end_dt]
                ).delete()
                logger.info(f"删除了{deleted_count}条时间范围内的旧交易数据")
            except Exception as e:
                logger.warning(f"删除旧数据时出错: {str(e)}")
        
        # 用于批量创建的数据列表
        batch_data = []
        batch_size = 100  # 每批创建的记录数
        
        while page <= total_pages:
            # 获取交易数据
            success, data = client.get_transaction(
                page=page,
                pagesize=page_size,
                purchaseStartDate=purchase_start_date,
                purchaseEndDate=purchase_end_date,
                queryDateType=query_date_type
            )

            
            if not success:
                error_msg = f"获取第{page}页交易数据失败: {data}"
                logger.error(error_msg)
                error_count += 1
                error_details.append(error_msg)
                break
            
            # 处理返回的数据
            if data and 'rows' in data:
                total_pages = (data.get('total', 0) + page_size - 1) // page_size
                
                # 处理每一条交易数据
                for row in data.get('rows', []):
                    try:
                        # 映射数据
                        mapped_data = map_transaction_data(row)
                    
                        # 使用批量创建方式替代update_or_create
                        batch_data.append(Transaction(**mapped_data))
                        
                        # 当累积到一定数量时批量创建
                        if len(batch_data) >= batch_size:
                            Transaction.objects.bulk_create(batch_data)
                            success_count += len(batch_data)
                            batch_data = []  # 清空批次数据
                            logger.info(f"批量创建了{success_count}条交易数据")
                        
                    except Exception as e:
                        error_msg = f"处理交易数据异常: {str(e)}"
                        logger.error(error_msg)
                        error_count += 1
                        error_details.append(error_msg)
            else:
                break
            
            page += 1
        
        # 处理剩余的批量数据
        if batch_data:
            Transaction.objects.bulk_create(batch_data)
            success_count += len(batch_data)
            logger.info(f"处理剩余数据，最终创建了{success_count}条交易数据")
        
        # 更新同步日志
        sync_log.status = 'success' if error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = success_count
        sync_log.error_count = error_count
        sync_log.response_message = json.dumps({
            'error_details': error_details,
            'total_processed': success_count + error_count
        })
        sync_log.save()
        
        # 返回成功响应
        return Response({
            'success': True,
            'message': f"交易数据同步完成",
            'data': {
                'sync_log_id': sync_log.id,
                'success_count': success_count,
                'error_count': error_count,
                'total_processed': success_count + error_count
            }
        })
    
    except Exception as e:
        # 记录异常
        logger.error(f"同步交易数据异常: {str(e)}")
        
        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.error_count = 1
        sync_log.response_message = str(e)
        sync_log.save()
        
        # 返回错误响应
        return Response({
            'success': False,
            'error': f"同步交易数据失败: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 流量分析数据映射函数
def map_traffic_analysis_data(data):
    """
    映射流量分析数据
    
    Args:
        data: 原始流量分析数据
    
    Returns:
        映射后的流量分析数据
    """
    # 映射基本信息
    mapped = {
        'market_id': data.get('marketId'),
        'market_name': data.get('marketName'),
        'parent_asin': data.get('parentAsin'),
        'msku': data.get('msku'),
        'asin': data.get('asin'),
        'sessions': data.get('sessions'),
        'browser_sessions': data.get('browserSessions'),
        'app_sessions': data.get('appSessions'),
        'page_views': data.get('pageViews'),
        'browser_page_views': data.get('browserPageViews'),
        'app_page_views': data.get('appPageViews'),
        'buy_box_per': data.get('buyBoxPer'),
        'units_ordered': data.get('unitsOrdered'),
        'units_ordered_b2b': data.get('unitsOrderedB2B'),
        'ordered_product_sales': data.get('orderedProductSales'),
        'ordered_product_sales_b2b': data.get('orderedProductSalesB2B'),
        'total_order_items': data.get('totalOrderItems'),
        'total_order_items_b2b': data.get('totalOrderItemsB2B'),
        'record_date': data.get('recordDate'),
    }
    
    # 过滤掉None值，避免更新时覆盖现有值
    # mapped = {k: v for k, v in mapped.items() if v is not None}
    
    return mapped


# 流量分析数据同步视图
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_traffic_analysis(request):
    """
    从Gerpgo同步流量分析数据
    根据传入的开始日期和结束日期，按天循环取数并将日期存入数据库
    :param request: 请求对象，包含同步参数(beginDate, endDate等)
    :return: 响应对象，包含同步结果
    """
    # 初始化日志记录器
    logger = logging.getLogger(__name__)  # 记录器名称为当前模块名
    logger.info(f"开始同步流量分析数据，参数：{request.data}")  # 记录同步开始信息
    
    # 创建同步日志记录
    sync_log = SyncLog.objects.create(
        sync_type='traffic_analysis',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"创建同步日志，批次ID：{sync_log.id}")  # 记录批次ID
    
    # 验证请求参数
    serializer = TrafficAnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"请求参数无效：{serializer.errors}")  # 记录错误信息
        return Response({
            'status': 'failed',
            'message': '请求参数无效',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        
        # 获取分页参数
        page = serializer.validated_data.get('page', 1)  # validated_data代表请求参数，get方法获取page参数，默认值为1
        pagesize = serializer.validated_data.get('pagesize', 100)
        
        # 获取日期参数
        beginDate = serializer.validated_data.get('beginDate')
        endDate = serializer.validated_data.get('endDate')

        # 如果缺乏日期参数使用近14天
        if not beginDate or not endDate:
            endDate = datetime.now().date()
            beginDate = endDate - timedelta(days=14)
            logger.info(f"使用近7天日期范围：{beginDate} - {endDate}")  # 记录日期范围

        # 确保日期是date类型
        if isinstance(beginDate, datetime):
            beginDate = beginDate.date()
        if isinstance(endDate, datetime):
            endDate = endDate.date()

        # 获取其他参数
        currency = serializer.validated_data.get('currency', 'YUAN')
        viewType = serializer.validated_data.get('viewType', 'day')

        # 初始化计数器
        total_success_count = 0
        total_error_count = 0
        error_details = []
        day_results = []  # 记录每天的同步结果

        # 按天循环取数
        current_date = beginDate
        while current_date <= endDate:
            logger.info(f"开始同步日期：{current_date}")
            day_success_count = 0
            day_error_count = 0
            current_page = page  # 每天从第1页开始
            total_pages = 1

            # 对当前日期进行分页循环
            while current_page <= total_pages:
                # 调用API，每次只查询当前日期的数据
                success, data = client.get_traffic_analysis(
                    page=current_page,
                    pagesize=pagesize,
                    currency=currency,
                    viewType=viewType,
                    beginDate=current_date,  # 开始日期设为当前日期
                    endDate=current_date     # 结束日期也设为当前日期，确保只查询单天数据
                )
                if not success:
                    error_msg = f"获取日期{current_date}第{current_page}页数据失败"
                    logger.error(error_msg)
                    day_error_count += 1
                    error_details.append(error_msg)
                    break

                if data and 'rows' in data:
                    total_pages = math.ceil(data.get('total', 0) / pagesize)  # 计算总页数
                    logger.info(f"日期{current_date}第{current_page}页数据，总页数：{total_pages}，总记录数：{data.get('total', 0)}")  # 记录分页信息

                    # 处理返回数据
                    for row in data.get('rows', []):
                        try:
                            # 使用映射函数解析数据
                            mapped_data = map_traffic_analysis_data(row)
                            
                            # 强制将record_date设置为当前循环的日期，确保日期存入数据库
                            mapped_data['record_date'] = current_date
                            
                            # 保存到数据库，使用唯一键避免重复
                            obj, created = TrafficAnalysis.objects.update_or_create(
                                record_date=current_date,  # 使用当前循环日期作为唯一键之一
                                market_id=mapped_data.get('market_id'),
                                msku=mapped_data.get('msku'),
                                asin=mapped_data.get('asin'),
                                parent_asin=mapped_data.get('parent_asin'),
                                defaults=mapped_data
                            )
                            if created:
                                logger.info(f"创建新记录：日期{current_date}-{mapped_data.get('market_name')}-{mapped_data.get('msku')}")  # 记录创建信息
                            else:
                                logger.info(f"更新记录：日期{current_date}-{mapped_data.get('market_name')}-{mapped_data.get('msku')}")  # 记录更新信息
                            day_success_count += 1
                        except Exception as e:
                            error_msg = f"处理日期{current_date}流量分析数据异常：{str(e)}"
                            logger.error(error_msg)
                            day_error_count += 1
                            error_details.append(error_msg)
                else:
                    break
                current_page += 1
            
            # 记录当天的同步结果
            day_results.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'success_count': day_success_count,
                'error_count': day_error_count
            })
            total_success_count += day_success_count
            total_error_count += day_error_count
            logger.info(f"日期{current_date}同步完成，成功：{day_success_count}，失败：{day_error_count}")
            
            # 移动到下一天
            current_date = current_date + timedelta(days=1)
        
        # 更新同步日志
        sync_log.status = 'success' if total_error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = total_success_count
        sync_log.failed_count = total_error_count
        sync_log.total_count = total_success_count + total_error_count
        sync_log.error_message = json.dumps({
            'error_details': error_details,
            'day_results': day_results,  # 记录每天的同步结果
            'total_processed': total_success_count + total_error_count
        }, ensure_ascii=False)  # 记录错误详情
        sync_log.save()

        # 返回成功响应
        return Response({
            'status': 'success',
            'message': f'数据同步完成，共同步{len(day_results)}天数据',
            'sync_log_id': sync_log.id,
            'date_range': f'{beginDate} 至 {endDate}',
            'total_processed': total_success_count + total_error_count,
            'success_count': total_success_count,
            'failed_count': total_error_count,
            'day_results': day_results  # 返回每天的详细结果
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"数据同步过程中发生异常：{str(e)}")  # 记录错误信息

        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.error_message = json.dumps({
            'error_details': [str(e)],
            'total_processed': 0
        }, ensure_ascii=False)  # 记录异常信息
        sync_log.save()  # 保存同步日志到数据库

        # 返回失败响应
        return Response({
            'status': 'failed',
            'message': '数据同步过程中发生异常',
            'sync_log_id': sync_log.id,
            'error_details': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 映射FBA库存完整数据
def map_fba_inventory_full_data(inventory_data):
    """将Gerpgo FBA库存完整数据映射为FBAInventory模型格式"""
    
    # 安全类型转换函数
    def safe_int(value, default=None):
        """安全转换为整数类型，处理空字符串、None和非法值（如'无限'）"""
        if value is None or value == '':
            return default
        # 处理特殊字符串（如中文的"无限"或英文的"Infinite"）
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ['infinite', '无限', 'inf', 'infinity', 'n/a', '-']:
                return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def safe_str(value, default=''):
        """安全转换为字符串类型，None返回空字符串"""
        if value is None:
            return default
        return str(value)
    
    # 只返回FBAInventory模型中定义的字段
    return {
        'create_time': inventory_data.get('createTime'),
        'warehouse_id': safe_int(inventory_data.get('warehouseId')),
        'warehouse_name': inventory_data.get('warehouseName'),
        'warehouse_country': inventory_data.get('warehouseCountry'),
        'msku': inventory_data.get('msku'),
        'fnsku': inventory_data.get('fnsku'),
        'asin': inventory_data.get('asin'),
        'single_quantity': safe_int(inventory_data.get('singleQuantity')),
        'product_delivery_days': safe_int(inventory_data.get('productDeliveryDays')),
        'purchase_plan_quantity': safe_int(inventory_data.get('purchasePlanQuantity')),
        'preassembly_plan_quantity': safe_int(inventory_data.get('preassemblyPlanQuantity')),
        'plan_quantity': safe_int(inventory_data.get('planQuantity')),
        'order_quantity': safe_int(inventory_data.get('orderQuantity')),
        'lot_no_quantity': safe_int(inventory_data.get('lotNoQuantity')),
        'pl_poLn_qty': safe_int(inventory_data.get('plPoLnQty')),
        'transfer_pending_inventory_qty': safe_int(inventory_data.get('transferPendingInventoryQty')),
        'transfer_pending_shipment_qty': safe_int(inventory_data.get('transferPendingShipmentQty')),
        'erp_shipped_qty': safe_int(inventory_data.get('erpShippedQty')),
        'erp_pending_inventory_qty': safe_int(inventory_data.get('erpPendingInventoryQty')),
        'in_transit_qty': safe_int(inventory_data.get('inTransitQty')),
        'working_quantity': safe_int(inventory_data.get('workingQuantity')),
        'shipped_quantity': safe_int(inventory_data.get('shippedQuantity')),
        'receiving_quantity': safe_int(inventory_data.get('receivingQuantity')),
        'inbound_total': safe_int(inventory_data.get('inboundTotal')),
        'available_quantity': safe_int(inventory_data.get('afnFulfillableQuantity')),
        'remote_available_quantity': safe_int(inventory_data.get('afnFulfillableQuantityRemote')),
        'local_available_quantity': safe_int(inventory_data.get('afnFulfillableQuantityLocal')),
        'fbm_available_quantity': safe_int(inventory_data.get('mfnFulfillableQuantity')),
        'unsellable_quantity': safe_int(inventory_data.get('unsellableQuantity')),
        'researching_quantity': safe_int(inventory_data.get('researchingQuantity')),
        'total_quantity': safe_int(inventory_data.get('totalQuantity')),
        'reserved_future_supply': safe_int(inventory_data.get('reservedFutureSupply')),
        'future_supply_buyable_quantity': safe_int(inventory_data.get('futureSupplyBuyable')),
        'historical_days_supply': safe_int(inventory_data.get('historicalDaysOfSupply')),
        'fba_min_quantity': safe_int(inventory_data.get('fbaMinimumInventoryLevel')),
        'fba_inventory_health_status': inventory_data.get('fbaInventoryLevelHealthStatus'),
        'reserved_quantity': safe_int(inventory_data.get('reserved')),
        'reserved_customer_orders': safe_int(inventory_data.get('reservedCustomerorders')),
        'reserved_fc_processing': safe_int(inventory_data.get('reservedProcessing')),
        'reserved_fc_transfer': safe_int(inventory_data.get('reservedTransfers')),
        'good_qty': safe_int(inventory_data.get('goodQty')),
        'defective_qty': safe_int(inventory_data.get('defectiveQty')),
        'unprocessed_reservation_qty': safe_int(inventory_data.get('unprocessedReservationQty')),
        'processed_reservation_qty': safe_int(inventory_data.get('processedReservationQty')),
        'reservation_qty': safe_int(inventory_data.get('reservationQty')),
        'available_qty': safe_int(inventory_data.get('availableQty')),
        'on_hand_qty': safe_int(inventory_data.get('onHandQty')),
        'total_inventory_qty': safe_int(inventory_data.get('totalInventoryQty')),
        'inventory_age_0_to_30_days': safe_int(inventory_data.get('invAge0To30Days')),
        'inventory_age_31_to_60_days': safe_int(inventory_data.get('invAge31To60Days')),
        'inventory_age_61_to_90_days': safe_int(inventory_data.get('invAge61To90Days')),
        'inventory_age_91_to_180_days': safe_int(inventory_data.get('invAge91To180Days')),
        'inventory_age_181_to_270_days': safe_int(inventory_data.get('invAge181To270Days')),
        'inventory_age_271_to_330_days': safe_int(inventory_data.get('invAge271To330Days')),
        'inventory_age_331_to_365_days': safe_int(inventory_data.get('invAge331To365Days')),
        'inventory_age_365_plus_days': safe_int(inventory_data.get('invAge365PlusDays')),
        'obsolete_qty': safe_int(inventory_data.get('obsoleteQty')),
        'avg_units_ordered_7_days': safe_int(inventory_data.get('avgUnitsOrdered7Days')),
        'avg_units_ordered_15_days': safe_int(inventory_data.get('avgUnitsOrdered15Days')),
        'avg_units_ordered_30_days': safe_int(inventory_data.get('avgUnitsOrdered30Days')),
        'available_turnover_days': safe_int(inventory_data.get('availableTurnoverDays')),
        'inventory_turnover_days': safe_int(inventory_data.get('inventoryTurnoverDays')),
        'in_transit_turnover_days': safe_int(inventory_data.get('inTransitTurnoverDays')),
        'total_turnover_days': safe_int(inventory_data.get('totalTurnoverDays')),
        'shipment_in_transit_turnover_days': safe_int(inventory_data.get('shipmentInTransitTurnoverDays')),
        'shipment_total_turnover_days': safe_int(inventory_data.get('shipmentTotalTurnoverDays'))
    }


# 同步完整FBA库存数据到新模型
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_fba_inventory_full_from_gerpgo(request):
    """
    从Gerpgo同步完整FBA库存数据到FBAInventory模型
    支持多种参数格式，确保与前端兼容
    """
    # 初始化日志记录器
    logger = logging.getLogger(__name__)
    logger.info(f"收到完整FBA库存同步请求，原始参数: {request.data}")
    
    # 创建同步日志记录
    sync_log = SyncLog.objects.create(
        sync_type='fba_inventory_full',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0
    )
    logger.info(f"创建同步日志，批次ID: {sync_log.id}")
    
    try:
        # 1. 参数预处理和兼容处理
        processed_data = request.data.copy()
        
        # 参数名映射，支持多种前端参数格式
        param_mapping = {
            'page_size': 'pagesize',
            'begin_date': 'last_updated_after',
            'end_date': 'last_updated_before',
            'warehouseIds': 'warehouse_country',
            'warehouse_id': 'warehouse_country',
            'currency': 'currency'
        }
        
        for source_param, target_param in param_mapping.items():
            if source_param in processed_data and target_param not in processed_data:
                if source_param == 'warehouseIds' and isinstance(processed_data[source_param], (list, str)):
                    # 特殊处理warehouseIds，提取第一个仓库ID作为国家信息
                    warehouse_ids = processed_data[source_param]
                    if isinstance(warehouse_ids, list) and warehouse_ids:
                        # 假设仓库ID格式为COUNTRY_XXXX
                        processed_data[target_param] = warehouse_ids[0].split('_')[0] if '_' in warehouse_ids[0] else warehouse_ids[0]
                    elif isinstance(warehouse_ids, str):
                        # 处理逗号分隔的字符串
                        first_id = warehouse_ids.split(',')[0].strip()
                        processed_data[target_param] = first_id.split('_')[0] if '_' in first_id else first_id
                else:
                    # 常规参数映射
                    processed_data[target_param] = processed_data[source_param]
        
        # 2. 参数验证
        serializer = FBAInventorySyncRequestSerializer(data=processed_data)
        if not serializer.is_valid():
            error_msg = f"FBA库存同步请求参数验证失败: {serializer.errors}"
            logger.error(error_msg)
            sync_log.status = 'failed'
            sync_log.error_message = error_msg
            sync_log.end_time = timezone.now()
            sync_log.save()
            return Response(
                {'status': 'error', 'message': error_msg, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3. 提取验证后的参数
        validated_data = serializer.validated_data
        page = validated_data.get('page', 1)
        pagesize = validated_data.get('pagesize', 100)
        warehouse_country = validated_data.get('warehouse_country')
        sku = validated_data.get('sku')
        last_updated_after = validated_data.get('last_updated_after')
        
        logger.info(f"参数验证成功，使用参数: page={page}, pagesize={pagesize}, "
                   f"warehouse_country={warehouse_country}, sku={sku}, last_updated_after={last_updated_after}")
        
        # 4. 初始化API客户端
        try:
            client = GerpgoAPIClient(
                appId=settings.GERPGO_APP_ID,
                appKey=settings.GERPGO_APP_KEY,
                base_url=settings.GERPGO_API_BASE_URL
            )
            logger.info("API客户端初始化成功")
        except Exception as e:
            error_msg = f"API客户端初始化失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            sync_log.status = 'failed'
            sync_log.error_message = error_msg
            sync_log.end_time = timezone.now()
            sync_log.save()
            return Response(
                {'status': 'error', 'message': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 5. 同步数据主循环
        success_count = 0
        failed_count = 0
        has_more = True
        max_pages = 1000  # 防止无限循环
        current_page = 1
        
        while has_more and current_page <= max_pages:
            logger.info(f"获取第{current_page}页完整FBA库存数据，每页{pagesize}条")
            
            # 构建API请求参数
            api_params = {
                'page': current_page,
                'pagesize': pagesize
            }
            
            # 添加可选筛选条件
            if warehouse_country:
                api_params['warehouse_country'] = warehouse_country
            if sku:
                api_params['sku'] = sku
            if last_updated_after:
                api_params['last_updated_after'] = last_updated_after
            
            # 调用API获取数据
            api_success, response = client.get_fba_inventory_page(**api_params)
            
            if not api_success:
                error_msg = f"获取完整FBA库存数据失败: {response.get('error', '未知错误')}"
                logger.error(error_msg)
                failed_count += 1
                break
            
            # 处理API响应
            if not isinstance(response, dict) or 'data' not in response:
                logger.error(f"API响应格式错误: 缺少data字段，响应内容: {response}")
                failed_count += 1
                break
            
            data = response['data']
            inventory_data = data.get('rows', []) if isinstance(data, dict) else []
            logger.info(f"从API获取到{len(inventory_data)}条库存数据")
            
            # 记录样本数据用于调试
            if inventory_data:
                sample = inventory_data[0]
                logger.debug(f"样本数据结构: {list(sample.keys())}")
                logger.debug(f"样本数据值: msku={sample.get('msku')}, warehouseName={sample.get('warehouseName')}, "
                           f"availableQuantity={sample.get('availableQuantity')}")
            
            # 如果没有数据，结束同步
            if not inventory_data:
                logger.info("未获取到更多库存数据，同步完成")
                has_more = False
                break
            
            # 更新总计数
            sync_log.total_count += len(inventory_data)
            
            # 处理并保存每条库存数据
            for idx, item_data in enumerate(inventory_data):
                try:
                    # 映射数据格式
                    inventory_data_mapped = map_fba_inventory_full_data(item_data)
                    
                    # 验证必要字段
                    required_fields = ['msku', 'warehouse_name', 'warehouse_country']
                    missing_fields = [field for field in required_fields if not inventory_data_mapped.get(field)]
                    if missing_fields:
                        logger.warning(f"跳过缺少必要字段的数据: {missing_fields}, 数据: {inventory_data_mapped}")
                        failed_count += 1
                        continue
                    
                    # 使用update_or_create保存数据
                    inventory, created = FBAInventory.objects.update_or_create(
                        msku=inventory_data_mapped.get('msku'),
                        asin=inventory_data_mapped.get('asin'),
                        fnsku=inventory_data_mapped.get('fnsku'),
                        warehouse_name=inventory_data_mapped.get('warehouse_name'),
                        warehouse_country=inventory_data_mapped.get('warehouse_country'),
                        # create_time=inventory_data_mapped.get('create_time'),
                        update_time=inventory_data_mapped.get('update_time'),
                        defaults=inventory_data_mapped
                    )
                    
                    inventory.save()
                    success_count += 1
                    
                    # 每100条记录日志一次，避免日志过多
                    if (idx + 1) % 100 == 0 or idx + 1 == len(inventory_data):
                        logger.info(f"已处理第{idx + 1}/{len(inventory_data)}条数据，成功: {success_count}, 失败: {failed_count}")
                    
                except Exception as db_error:
                    logger.error(f"保存库存数据失败 (索引: {idx}): {str(db_error)}")
                    logger.error(f"失败的数据: {item_data}")
                    failed_count += 1
            
            # 计算是否还有更多数据
            try:
                total = data.get('total', 0) if isinstance(data, dict) else 0
                current_api_page = data.get('page', current_page) if isinstance(data, dict) else current_page
                page_size_var = data.get('pagesize', pagesize) if isinstance(data, dict) else pagesize
                
                # 计算总页数
                if page_size_var > 0:
                    total_pages = (total + page_size_var - 1) // page_size_var
                else:
                    total_pages = 1
                
                has_more = current_api_page < total_pages
                current_page = current_api_page + 1
                
                logger.info(f"当前同步进度: 第{current_api_page}/{total_pages}页，已处理{sync_log.total_count}条数据")
            except Exception as e:
                logger.error(f"计算分页信息失败: {str(e)}")
                has_more = False
        
        # 6. 更新同步日志并返回结果
        sync_log.status = 'success' if failed_count == 0 else 'partial_success'
        sync_log.success_count = success_count
        sync_log.failed_count = failed_count
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        logger.info(f"完整FBA库存同步完成，批次ID: {sync_log.id}，成功 {success_count} 条，失败 {failed_count} 条")
        
        return Response({
            'status': 'success',
            'message': f'完整FBA库存同步完成，成功 {success_count} 条，失败 {failed_count} 条',
            'sync_log_id': sync_log.id,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_count': sync_log.total_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # 捕获所有未预期的异常
        logger.error(f"完整FBA库存同步过程发生异常: {str(e)}", exc_info=True)
        
        # 更新同步日志为失败状态
        sync_log.status = 'failed'
        sync_log.error_message = str(e)
        sync_log.end_time = timezone.now()
        sync_log.save()
        
        return Response({
            'status': 'error',
            'message': f'完整FBA库存同步失败: {str(e)}',
            'sync_log_id': sync_log.id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 映射月度仓储费数据
def map_mon_storage_fee_data(mon_storage_fee_data):
    """映射月度仓储费数据"""
    return {
        'market_ids': mon_storage_fee_data.get('marketIds'),
        'market_id': mon_storage_fee_data.get('marketId'),
        'country_code': mon_storage_fee_data.get('countryCode'),
        'seller_sku': mon_storage_fee_data.get('sellerSku'),
        'fnsku': mon_storage_fee_data.get('fnsku'),
        'asin': mon_storage_fee_data.get('asin'),
        'fulfillment_center': mon_storage_fee_data.get('fulfillmentCenter'),
        'longest_side': mon_storage_fee_data.get('longestSide'),
        'median_side': mon_storage_fee_data.get('medianSide'),
        'shortest_side': mon_storage_fee_data.get('shortestSide'),
        'measurement_units': mon_storage_fee_data.get('measurementUnits'),
        'weight': mon_storage_fee_data.get('weight'),
        'weight_units': mon_storage_fee_data.get('weightUnits'),
        'item_volume': mon_storage_fee_data.get('itemVolume'),
        'volume_units': mon_storage_fee_data.get('volumeUnits'),
        'product_size_tier': mon_storage_fee_data.get('productSizeTier'),
        'average_quantity_on_hand': mon_storage_fee_data.get('averageQuantityOnHand'),
        'average_quantity_pending_removal': mon_storage_fee_data.get('averageQuantityPendingRemoval'),
        'estimated_total_item_volume': mon_storage_fee_data.get('estimatedTotalItemVolume'),
        'month_of_charge': mon_storage_fee_data.get('monthOfCharge'),
        'storage_rate': mon_storage_fee_data.get('storageRate'),
        'currency': mon_storage_fee_data.get('currency'),
        'estimated_monthly_storage_fee': mon_storage_fee_data.get('estimatedMonthlyStorageFee'),
        'category': mon_storage_fee_data.get('category'),
        'year': mon_storage_fee_data.get('year'),
        'month': mon_storage_fee_data.get('month'),
        'storage_fee': mon_storage_fee_data.get('storageFee'),
    }



# 同步月度仓储费数据
@api_view(['POST'])# 允许POST请求
@permission_classes([AllowAny]) # 允许所有用户访问
def sync_mon_storage_fee(request):
    """
    从Gerpgo同步阅读仓储费数据到数据库
    :param request: 请求对象，包含同步参数
    :return: 响应对象，包含同步结果
    """
    # 初始化日志记录器
    logger = logging.getLogger(__name__) # __name__ 是当前模块的名称
    logger.info(f"收到月度仓储费同步请求，参数：{request.data}") # 记录请求参数
    # 创建同步日志记录
    sync_log = SyncLog.objects.create(
        sync_type = 'monthly_storage_fee',
        status = 'running',
        total_count = 0,
        success_count=0,
        failed_count = 0
    )
    logger.info(f"创建同步日志，批次ID：{sync_log.id}") # 记录批次ID

    # 验证请求参数
    serializer = MonStorageFeeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"请求参数验证失败：{serializer.errors}") # 记录错误信息
        return Response({
            'status': 'error',
            'message': '请求参数验证失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        # 获取分页参数
        page = serializer.validated_data['page']
        pagesize = serializer.validated_data['pagesize']

        # 获取日期参数
        year = serializer.validated_data.get('year')
        month = serializer.validated_data.get('month')

        # 初始化分页参数
        total_pages = 1
        success_count = 0
        error_count = 0
        error_details = []

        while page <= total_pages:
            # 获取月度仓储费数据
            success, data = client.get_month_storage_fee(
                page=page,
                pagesize=pagesize,
                year=year,
                month=month
            )
            if not success:
                error_msg = f"获取第{page}页数据失败：{data}"
                logger.error(error_msg) # 记录错误信息
                error_count += 1
                error_details.append(error_msg)
                break

            # 处理返回数据
            if data and 'data' in data:
                total_pages = math.ceil(data['data'].get('total', 0) / pagesize) # 计算总页数
                """
                total_pages计算解释说明：
                假设总共有100条数据，每页显示10条，那么总页数就是100/10=10页。
                假设总共有101条数据，每页显示10条，那么总页数就是101/10=11页。
                所以，total_pages的计算方法就是：总数据条数/每页显示条数，向上取整。
                """
                # 处理返回数据
                for row in data['data'].get('rows',[]):
                    try:
                        # 解析数据
                        mapped_data = map_mon_storage_fee_data(row)
                        # 使用update_or_create来更新或创建数据
                        updated,created = MonStorageFee.objects.update_or_create(
                            year=mapped_data['year'],
                            month=mapped_data['month'],
                            market_id=mapped_data['market_id'],
                            fnsku=mapped_data['fnsku'],
                            fulfillment_center=mapped_data['fulfillment_center'],
                            defaults=mapped_data
                        )
                        if created: # 如果是新创建的记录，增加成功计数
                            logger.info(f"创建新记录：{mapped_data['market_id']}-{mapped_data['fnsku']}") # 记录创建信息
                        else: # 如果是已存在的记录，记录更新信息
                            logger.info(f"更新记录：{mapped_data['market_id']}-{mapped_data['fnsku']}") # 记录更新信息
                        success_count += 1 # 增加成功计数
                    except Exception as e:
                        error_msg = f"处理月度仓储费数据异常：{str(e)}"
                        logger.error(error_msg)
                        error_count += 1
                        error_details.append(error_msg)
            else:
                break
            
            page += 1 # 增加分页参数

        # 更新同步日志
        sync_log.status = 'success' if error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = success_count
        sync_log.failed_count = error_count
        sync_log.error_message = json.dumps({
        'error_details': error_details,
        'total_processed': success_count + error_count
        }) # 记录错误详情
        sync_log.save()

        # 返回成功相应
        return Response({
            'status': 'success',
            'message': '数据同步完成',
            'sync_log_id': sync_log.id,
            'total_processed': success_count + error_count,
            'success_count': success_count,
            'failed_count': error_count
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"数据同步过程中发生异常：{str(e)}") # 记录错误信息
        
        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.failed_count = error_count
        sync_log.error_message = json.dumps({
        'error_details': [str(e)],
        'total_processed': success_count + error_count
        }) # 记录异常信息
        sync_log.save() # 保存同步日志到数据库

        # 返回失败相应
        return Response({
            'status': 'failed',
            'message': '数据同步过程中发生异常',
            'sync_log_id': sync_log.id,
            'total_processed': success_count + error_count,
            'failed_count': error_count,
            'error_details': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# 利润分析数据映射
def map_profit_data(profit_data):
    return {
        'market_id':profit_data.get('marketId'),
        'warehouse_id':profit_data.get('warehouseId'),
        'market_name':profit_data.get('marketName'),
        'country_id':profit_data.get('countryId'),
        'country_name':profit_data.get('countryName'),
        'currency':profit_data.get('currency'),
        'msku':profit_data.get('msku'),
        'sku':profit_data.get('sku'),
        'asin':profit_data.get('asin'),
        'statistics_date':profit_data.get('statisticsDate'),
        'order_product_sales':profit_data.get('orderProductSales'),
        'discount_cost_sales':profit_data.get('discountCostSales'),
        'discount_cost':profit_data.get('discountCost'),
        'order_product_sales_b2b':profit_data.get('orderProductSalesB2B'),
        'orders':profit_data.get('orders'),
        'order_items':profit_data.get('orderItems'),
        'order_items_b2b':profit_data.get('orderItemsB2B'),
        'units_ordered':profit_data.get('unitsOrdered'),
        'units_ordered_b2b':profit_data.get('unitsOrderedB2B'),
        'units_ordered_traffic':profit_data.get('unitsOrderedTraffic'),
        'avg_order_items':profit_data.get('avgOrderItems'),
        'avg_order_items_sales':profit_data.get('avgOrderItemsSales'),
        'avg_units_ordered_sales':profit_data.get('avgUnitsOrderedSales'),
        'patch_units_ordered':profit_data.get('patchUnitsOrdered'),
        'multi_channel_orders':profit_data.get('multiChannelOrders'),
        'refunds':profit_data.get('refunds'),
        'returns':profit_data.get('returns'),
        'returns_sellable':profit_data.get('returnsSellable'),
        'returns_purchase_cost':profit_data.get('returnsPurchaseCost'),
        'returns_arrive_cost':profit_data.get('returnsArriveCost'),
        'refund_cost':profit_data.get('refundCost'),
        'return_product_sales':profit_data.get('returnProductSales'),
        'refund_discount_cost':profit_data.get('refundDiscountCost'),
        'refund_tax_cost':profit_data.get('refundTaxCost'),
        'order_ids':profit_data.get('orderIds'),
        'ads_impressions':profit_data.get('adsImpressions'),
        'ads_clicks':profit_data.get('adsClicks'),
        'ads_orders':profit_data.get('adsOrders'),
        'ads_sales':profit_data.get('adsSales'),
        'ads_spend':profit_data.get('adsSpend'),
        'ads_item_orders':profit_data.get('adsItemOrders'),
        'ads_natural_orders':profit_data.get('adsNaturalOrders'),
        'ads_item_sales':profit_data.get('adsItemSales'),
        'commission_cost':profit_data.get('commissionCost'),
        'shipping_cost':profit_data.get('shippingCost'),
        'fba_shipping_cost':profit_data.get('fbaShippingCost'),
        'fbm_shipping_cost':profit_data.get('fbmShippingCost'),
        'amazon_tax_cost':profit_data.get('amazonTaxCost'),
        'others_cost':profit_data.get('othersCost'),
        'purchase_cost':profit_data.get('purchaseCost'),
        'arrive_cost':profit_data.get('arriveCost'),
        'product_shipping_cost':profit_data.get('productShippingCost'),
        'vat_cost':profit_data.get('vatCost'),
        'sales_gross_profit':profit_data.get('salesGrossProfit'),
        'sales_net_profit':profit_data.get('salesNetProfit'),
        'patch_amazon_cost':profit_data.get('patchAmazonCost'),
        'patch_purchase_cost':profit_data.get('patchPurchaseCost'),
        'patch_arrive_cost':profit_data.get('patchArriveCost'),
        'multichannel_amazon_cost':profit_data.get('multichannelAmazonCost'),
        'multichannel_purchase_cost':profit_data.get('multichannelPurchaseCost'),
        'multichannel_arrive_cost':profit_data.get('multichannelArriveCost'),
        'storage_fee':profit_data.get('storageFee'),
        'selling_price':profit_data.get('sellingPrice'),
        'fba_quantity':profit_data.get('fbaQuantity'),
        'fba_turnover':profit_data.get('fbaTurnover'),
        'fbm_quantity':profit_data.get('fbmQuantity'),
        'fbm_turnover':profit_data.get('fbmTurnover'),
        'main_seller_rank':profit_data.get('mainSellerRank'),
        'seller_rank':profit_data.get('sellerRank'),
        'seller_rank_category':profit_data.get('sellerRankCategory'),
        'main_seller_rank_category':profit_data.get('mainSellerRankCategory'),
        'star':profit_data.get('star'),
        'review_quantity':profit_data.get('reviewQuantity'),
        'platform_fee':profit_data.get('platformFee'),
        'fulfillment':profit_data.get('fulfillment'),
        'reserved_transfers':profit_data.get('reservedTransfers'),
        'reserved_trocessing':profit_data.get('reservedTrocessing'),
        'plan_storage_quantity':profit_data.get('planStorageQuantity'),
        'shipped_quantity':profit_data.get('shippedQuantity'),
        'receiving_quantity':profit_data.get('receivingQuantity'),
        'deal':profit_data.get('deal'),
        'coupon':profit_data.get('coupon'),
    }


# 同步销售利润分析数据
@api_view(['POST'])# 允许POST请求
@permission_classes([AllowAny]) # 允许所有用户访问
def sync_profit_analysis(request):# request代表POST请求体
    """
    从Gerpgo同步销售利润分析数据
    根据传入的开始日期和结束日期，按天循环取数并将日期存入数据库
    :param request: 请求对象，包含同步参数(beginDate, endDate等)
    :return: 响应对象，包含同步结果
    """
    # 初始化日志记录器
    logger = logging.getLogger(__name__) # 记录器名称为当前模块名
    logger.info(f"开始同步销售利润分析数据，参数：{request.data}") # 记录同步开始信息
    # 创建同步日志记录
    sync_log = SyncLog.objects.create(
        sync_type='profit_analysis',
        status='running',
        total_count = 0,
        success_count = 0,
        failed_count = 0
    )
    logger.info(f"创建同步日志，批次ID：{sync_log.id}") # 记录批次ID
    # 验证请求参数
    serializer = ProfitAnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"请求参数无效：{serializer.errors}") # 记录错误信息
        return Response({
            'status': 'failed',
            'message': '请求参数无效',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 初始化API客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )
        # 获取分页参数
        page = serializer.validated_data.get('page', 1) # validated_data代表请求参数，get方法获取page参数，默认值为1
        pagesize = serializer.validated_data.get('pageSize', 100)
        # 获取日期参数，同时支持两种命名方式
        beginDate = serializer.validated_data.get('beginDate')
        endDate = serializer.validated_data.get('endDate')
        
        # 同时检查下划线命名方式
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        # 优先使用start_date和end_date，如果存在的话
        if start_date and end_date:
            beginDate = start_date
            endDate = end_date
            logger.info(f"使用下划线命名方式的日期范围：{beginDate} - {endDate}")
        
        # 如果缺乏日期参数使用近7天
        if not beginDate or not endDate:
            endDate = datetime.now().date()
            beginDate = endDate - timedelta(days=7)
            logger.info(f"使用近7天日期范围：{beginDate} - {endDate}") # 记录日期范围

        # 确保日期是date类型
        if isinstance(beginDate, datetime):
            beginDate = beginDate.date()
        if isinstance(endDate, datetime):
            endDate = endDate.date()

        # 获取其他参数
        type = serializer.validated_data.get('type', 'MSKU')
        showCurrencyType = serializer.validated_data.get('showCurrencyType', 'YUAN')

        # 初始化计数器
        total_success_count = 0
        total_error_count = 0
        error_details = []
        day_results = []  # 记录每天的同步结果

        # 按天循环取数
        current_date = beginDate
        while current_date <= endDate:
            logger.info(f"开始同步日期：{current_date}")
            day_success_count = 0
            day_error_count = 0
            current_page = page
            total_pages = 1

            # 对当前日期进行分页循环
            while current_page <= total_pages:
                # 调用API，每次只查询当前日期的数据
                success, data = client.get_financial_analysis(
                    page=current_page,
                    pagesize=pagesize,
                    type=type,
                    showCurrencyType=showCurrencyType,
                    beginDate=current_date,  # 开始日期设为当前日期
                    endDate=current_date     # 结束日期也设为当前日期，确保只查询单天数据
                )
                if not success:
                    error_msg = f"获取日期{current_date}第{current_page}页数据失败"
                    logger.error(error_msg)
                    day_error_count += 1
                    error_details.append(error_msg)
                    break

                if data and 'data' in data:
                    total_pages = math.ceil(data['data'].get('total', 0) / pagesize) # 计算总页数
                    logger.info(f"日期{current_date}第{current_page}页数据，总页数：{total_pages}，总记录数：{data['data'].get('total', 0)}") # 记录分页信息

                    # 处理返回数据
                    for row in data['data'].get('rows', []):
                        try:
                            # 使用映射函数解析数据
                            mapped_data = map_profit_data(row)
                            
                            # 强制将statistics_date设置为当前循环的日期，确保日期存入数据库
                            mapped_data['statistics_date'] = current_date
                            
                            # 保存到数据库，使用唯一键避免重复
                            obj, created = ProfitAnalysis.objects.update_or_create(
                                statistics_date=current_date,  # 使用当前循环日期作为唯一键之一
                                market_id=mapped_data.get('market_id'),
                                msku=mapped_data.get('msku'),
                                asin=mapped_data.get('asin'),
                                defaults=mapped_data
                            )
                            if created:
                                logger.info(f"创建新记录：日期{current_date}-{mapped_data.get('market_name')}-{mapped_data.get('msku')}") # 记录创建信息
                            else:
                                logger.info(f"更新记录：日期{current_date}-{mapped_data.get('market_name')}-{mapped_data.get('msku')}") # 记录更新信息
                            day_success_count += 1
                        except Exception as e:
                            error_msg = f"处理日期{current_date}销售利润分析数据异常：{str(e)}"
                            logger.error(error_msg)
                            day_error_count += 1
                            error_details.append(error_msg)
                else:
                    break
                current_page += 1
            
            # 记录当天的同步结果
            day_results.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'success_count': day_success_count,
                'error_count': day_error_count
            })
            total_success_count += day_success_count
            total_error_count += day_error_count
            logger.info(f"日期{current_date}同步完成，成功：{day_success_count}，失败：{day_error_count}")
            
            # 移动到下一天
            current_date = current_date + timedelta(days=1)
        
        # 更新同步日志
        sync_log.status = 'success' if total_error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = total_success_count
        sync_log.failed_count = total_error_count
        sync_log.total_count = total_success_count + total_error_count
        sync_log.error_message = json.dumps({
            'error_details': error_details,
            'day_results': day_results,  # 记录每天的同步结果
            'total_processed': total_success_count + total_error_count
        }, ensure_ascii=False) # 记录错误详情
        sync_log.save()

        # 返回成功响应
        return Response({
            'status': 'success',
            'message': f'数据同步完成，共同步{len(day_results)}天数据',
            'sync_log_id': sync_log.id,
            'date_range': f'{beginDate} 至 {endDate}',
            'total_processed': total_success_count + total_error_count,
            'success_count': total_success_count,
            'failed_count': total_error_count,
            'day_results': day_results  # 返回每天的详细结果
        }, status=status.HTTP_200_OK)        
    
    except Exception as e:
        logger.error(f"数据同步过程中发生异常：{str(e)}") # 记录错误信息

        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.error_message = json.dumps({
            'error_details': [str(e)],
            'total_processed': 0
        }, ensure_ascii=False) # 记录异常信息
        sync_log.save() # 保存同步日志到数据库

        # 返回失败响应
        return Response({
            'status': 'failed',
            'message': '数据同步过程中发生异常',
            'sync_log_id': sync_log.id,
            'error_details': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 移动平均预测方法
def moving_average_forecast(sales_data, window_size=7, forecast_period=30):
    """
    使用移动平均法进行销售预测
    
    Args:
        sales_data: 历史销售数据列表
        window_size: 移动窗口大小
        forecast_period: 预测周期
    
    Returns:
        预测结果列表
    """
    if len(sales_data) < window_size:
        # 数据不足时，返回平均值
        avg_sales = sum(sales_data) / len(sales_data) if sales_data else 0
        return [avg_sales] * forecast_period
    
    # 计算移动平均
    forecast = []
    for i in range(forecast_period):
        # 使用最近的window_size个数据点计算平均值
        recent_avg = sum(sales_data[-window_size:]) / window_size
        forecast.append(recent_avg)
        # 将预测值添加到数据中，用于下一次预测
        sales_data.append(recent_avg)
    
    return forecast


# 线性回归预测方法
def linear_regression_forecast(dates, sales_data, forecast_period=30):
    """
    使用线性回归进行销售预测
    
    Args:
        dates: 日期列表
        sales_data: 历史销售数据列表
        forecast_period: 预测周期
    
    Returns:
        预测结果列表
    """
    if len(sales_data) < 2:
        # 数据不足时，返回平均值
        avg_sales = sum(sales_data) / len(sales_data) if sales_data else 0
        return [avg_sales] * forecast_period
    
    # 准备特征数据
    X = np.array([i for i in range(len(dates))]).reshape(-1, 1)
    y = np.array(sales_data)
    
    # 训练模型
    model = LinearRegression()
    model.fit(X, y)
    
    # 预测
    next_X = np.array([i for i in range(len(dates), len(dates) + forecast_period)]).reshape(-1, 1)
    forecast = model.predict(next_X).tolist()
    
    # 确保预测值不为负数
    forecast = [max(0, f) for f in forecast]
    
    return forecast


# 季节性预测方法
def seasonal_forecast(dates, sales_data, forecast_period=30):
    """
    考虑季节性的销售预测（简单实现，按周季节性）
    
    Args:
        dates: 日期列表
        sales_data: 历史销售数据列表
        forecast_period: 预测周期
    
    Returns:
        预测结果列表
    """
    if len(sales_data) < 14:  # 需要至少两周的数据来计算周季节性
        # 数据不足时，使用移动平均
        return moving_average_forecast(sales_data, window_size=7, forecast_period=forecast_period)
    
    # 计算每天的平均销量（按周几）
    weekday_avg = {}
    for i, d in enumerate(dates):
        weekday = d.weekday()
        if weekday not in weekday_avg:
            weekday_avg[weekday] = []
        weekday_avg[weekday].append(sales_data[i])
    
    # 计算周几平均值
    for weekday in weekday_avg:
        weekday_avg[weekday] = sum(weekday_avg[weekday]) / len(weekday_avg[weekday])
    
    # 预测未来销量
    forecast = []
    last_date = dates[-1]
    
    for i in range(forecast_period):
        next_date = last_date + timedelta(days=i+1)
        weekday = next_date.weekday()
        # 使用对应周几的平均值作为预测
        forecast.append(weekday_avg.get(weekday, sum(sales_data) / len(sales_data)))
    
    return forecast

# 计算库存周转天数
def calculate_turnover_days(available_quantity, reserved_quantity, daily_sales_rate):
    """
    计算库存周转天数
    
    Args:
        available_quantity: 可售库存
        reserved_quantity: 预留库存
        daily_sales_rate: 日均销售率
    
    Returns:
        周转天数
    """
    if daily_sales_rate <= 0:
        return float('inf')  # 无销量时周转天数为无穷大
    
    total_available = available_quantity + reserved_quantity
    return total_available / daily_sales_rate

# 生成销售预估
def generate_sales_forecast(market_name, asin, parent_asin, msku, forecast_method, lookback_period=90, forecast_months=12):
    """
    为指定的ASIN和市场生成销售预估
    
    Args:
        market_name: 市场名称
        asin: ASIN
        parent_asin: 父ASIN
        msku: MSKU
        forecast_method: 预测方法
        lookback_period: 回看历史天数
        forecast_months: 预测月数
    
    Returns:
        预估结果字典
    """
    logger = logging.getLogger(__name__)
    
    # 1. 获取历史销售数据
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_period)
    
    # 查询TrafficAnalysis表获取历史销量
    sales_history = TrafficAnalysis.objects.filter(
        market_name=market_name,
        asin=asin,
        record_date__range=(start_date, end_date)
    ).order_by('record_date')
    
    # 准备历史数据
    dates = []
    units_ordered = []
    sales_amounts = []
    
    for record in sales_history:
        dates.append(record.record_date)
        units_ordered.append(record.units_ordered or 0)
        sales_amounts.append(record.ordered_product_sales or 0)
    
    # 2. 获取当前库存数据
    latest_inventory = FBAInventory.objects.filter(
        asin=asin
    ).order_by('-add_time').first()
    
    available_quantity = latest_inventory.available_quantity if latest_inventory else 0
    reserved_quantity = latest_inventory.reserved_quantity if latest_inventory else 0
    
    # 3. 计算日均销售率
    daily_sales_rate = sum(units_ordered) / len(units_ordered) if units_ordered else 0
    avg_daily_sales_amount = sum(sales_amounts) / len(sales_amounts) if sales_amounts else 0
    
    # 4. 计算周转天数
    turnover_days = calculate_turnover_days(available_quantity, reserved_quantity, daily_sales_rate)
    
    # 5. 预测未来销售
    forecast_period = forecast_months * 30  # 简化为每月30天
    
    if forecast_method == 'moving_average':
        forecasted_units_daily = moving_average_forecast(units_ordered.copy(), window_size=7, forecast_period=forecast_period)
    elif forecast_method == 'linear_regression':
        forecasted_units_daily = linear_regression_forecast(dates, units_ordered, forecast_period=forecast_period)
    elif forecast_method == 'seasonal':
        forecasted_units_daily = seasonal_forecast(dates, units_ordered, forecast_period=forecast_period)
    else:
        # 默认使用移动平均
        forecasted_units_daily = moving_average_forecast(units_ordered.copy(), window_size=7, forecast_period=forecast_period)
    
    # 6. 按月汇总预测结果
    monthly_forecasts = []
    for month in range(forecast_months):
        # 计算该月的预测天数（这里简化为30天）
        month_days = 30
        start_idx = month * 30
        end_idx = min(start_idx + month_days, forecast_period)
        
        # 汇总该月预测销量
        month_forecast = sum(forecasted_units_daily[start_idx:end_idx])
        monthly_forecasts.append(round(month_forecast))
    
    # 7. 计算总预测销量和销售额
    total_forecasted_units = sum(monthly_forecasts)
    total_forecasted_sales = total_forecasted_units * avg_daily_sales_amount if daily_sales_rate > 0 else 0
    
    # 构建预估结果
    forecast_result = {
        'market_name': market_name,
        'asin': asin,
        'parent_asin': parent_asin,
        'msku': msku,
        'current_available_quantity': available_quantity,
        'current_reserved_quantity': reserved_quantity,
        'daily_sales_rate': daily_sales_rate,
        'turnover_days': turnover_days,
        'forecast_method': forecast_method,
        'forecast_start_date': end_date + timedelta(days=1),
        'forecast_end_date': end_date + timedelta(days=forecast_period),
        'forecasted_units': total_forecasted_units,
        'forecasted_sales': total_forecasted_sales,
    }
    
    # 添加月度预测
    for i, forecast in enumerate(monthly_forecasts):
        forecast_result[f'month_{i+1}_forecast'] = forecast
    
    return forecast_result



# 生成销售预估API
@api_view(['POST'])
@permission_classes([AllowAny])
def generate_forecasts(request):
    """
    批量生成销售预估
    
    请求参数：
    - market_ids: 市场ID列表（可选）
    - market_names: 市场名称列表（可选）
    - asins: ASIN列表（可选）
    - forecast_method: 预测方法（必填，可选值：moving_average, linear_regression, seasonal）
    - lookback_period: 回看历史天数（可选，默认90天）
    - forecast_months: 预测月数（可选，默认12个月）
    - confidence_level: 置信水平（可选，默认0.95）
    """
    logger = logging.getLogger(__name__)
    logger.info(f"收到销售预估请求: {request.data}")
    
    # 验证请求参数
    serializer = SalesForecastRequestSerializer(data=request.data)
    if not serializer.is_valid():
        logger.error(f"销售预估请求参数验证失败: {serializer.errors}")
        return Response({
            'status': 'error',
            'message': '参数验证失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    
    # 获取查询参数
    market_ids = validated_data.get('market_ids', [])
    market_names = validated_data.get('market_names', [])
    asins = validated_data.get('asins', [])
    forecast_method = validated_data.get('forecast_method')
    lookback_period = validated_data.get('lookback_period')
    forecast_months = validated_data.get('forecast_months')
    
    try:
        # 1. 构建查询以获取需要预估的ASIN和市场组合
        query = Q()
        
        if market_ids:
            query &= Q(market_id__in=market_ids)
        if market_names:
            query &= Q(market_name__in=market_names)
        if asins:
            query &= Q(asin__in=asins)
        
        # 获取所有符合条件的唯一ASIN和市场组合
        # 从TrafficAnalysis中获取最近有销售记录的组合
        recent_date = date.today() - timedelta(days=30)
        product_combinations = TrafficAnalysis.objects.filter(
            query,
            record_date__gte=recent_date
        ).values('market_name', 'asin', 'parent_asin').distinct()
        
        # 获取MSKU信息（从FBAInventory中关联）
        asin_to_msku = {}
        inventory_records = FBAInventory.objects.filter(
            asin__in=[pc['asin'] for pc in product_combinations]
        ).order_by('asin', '-add_time')
        
        for record in inventory_records:
            if record.asin not in asin_to_msku:
                asin_to_msku[record.asin] = record.msku
        
        # 2. 为每个组合生成预估
        success_count = 0
        error_count = 0
        errors = []
        
        for combo in product_combinations:
            try:
                market_name = combo['market_name']
                asin = combo['asin']
                parent_asin = combo['parent_asin']
                msku = asin_to_msku.get(asin, '')
                
                # 生成预估
                forecast_result = generate_sales_forecast(
                    market_name=market_name,
                    asin=asin,
                    parent_asin=parent_asin,
                    msku=msku,
                    forecast_method=forecast_method,
                    lookback_period=lookback_period,
                    forecast_months=forecast_months
                )
                
                # 保存预估结果到数据库
                forecast, created = SalesForecast.objects.update_or_create(
                    market_name=market_name,
                    asin=asin,
                    forecast_method=forecast_method,
                    defaults=forecast_result
                )
                
                success_count += 1
                
                # 每处理10个记录日志一次
                if success_count % 10 == 0:
                    logger.info(f"已生成 {success_count} 个销售预估")
                    
            except Exception as e:
                logger.error(f"生成预估失败 for {combo['market_name']} - {combo['asin']}: {str(e)}")
                error_count += 1
                errors.append({
                    'market_name': combo.get('market_name'),
                    'asin': combo.get('asin'),
                    'error': str(e)
                })
        
        # 3. 返回结果
        return Response({
            'status': 'success' if error_count == 0 else 'partial_success',
            'message': f'销售预估生成完成，成功 {success_count} 个，失败 {error_count} 个',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"生成销售预估过程发生异常: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'生成销售预估失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 获取销售预估数据API
@api_view(['GET'])
@permission_classes([AllowAny])
def get_sales_forecasts(request):
    """
    获取销售预估数据，支持分页和过滤
    
    查询参数：
    - market_names: 市场名称列表（可选）
    - asins: ASIN列表（可选）
    - forecast_method: 预测方法（可选）
    - page: 页码（可选，默认1）
    - pagesize: 每页数量（可选，默认20）
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 获取查询参数
        market_names = request.GET.getlist('market_names')
        asins = request.GET.getlist('asins')
        forecast_method = request.GET.get('forecast_method')
        page = int(request.GET.get('page', 1))
        pagesize = int(request.GET.get('pagesize', 20))
        
        # 构建查询
        query = Q()
        
        if market_names:
            query &= Q(market_name__in=market_names)
        if asins:
            query &= Q(asin__in=asins)
        if forecast_method:
            query &= Q(forecast_method=forecast_method)
        
        # 查询数据
        forecasts = SalesForecast.objects.filter(query).order_by('-generated_at')
        
        # 分页处理
        total_count = forecasts.count()
        start_index = (page - 1) * pagesize
        end_index = start_index + pagesize
        paginated_forecasts = forecasts[start_index:end_index]
        
        # 格式化数据
        result_data = []
        for forecast in paginated_forecasts:
            data = {
                'id': forecast.id,
                'market_id': forecast.market_id,
                'market_name': forecast.market_name,
                'asin': forecast.asin,
                'parent_asin': forecast.parent_asin,
                'msku': forecast.msku,
                'current_available_quantity': forecast.current_available_quantity,
                'current_reserved_quantity': forecast.current_reserved_quantity,
                'turnover_days': float(forecast.turnover_days) if forecast.turnover_days else None,
                'daily_sales_rate': float(forecast.daily_sales_rate) if forecast.daily_sales_rate else None,
                'forecast_method': forecast.forecast_method,
                'forecast_start_date': forecast.forecast_start_date.strftime('%Y-%m-%d') if forecast.forecast_start_date else None,
                'forecast_end_date': forecast.forecast_end_date.strftime('%Y-%m-%d') if forecast.forecast_end_date else None,
                'forecasted_units': forecast.forecasted_units,
                'forecasted_sales': float(forecast.forecasted_sales) if forecast.forecasted_sales else None,
                'monthly_forecasts': [
                    forecast.month_1_forecast,
                    forecast.month_2_forecast,
                    forecast.month_3_forecast,
                    forecast.month_4_forecast,
                    forecast.month_5_forecast,
                    forecast.month_6_forecast,
                    forecast.month_7_forecast,
                    forecast.month_8_forecast,
                    forecast.month_9_forecast,
                    forecast.month_10_forecast,
                    forecast.month_11_forecast,
                    forecast.month_12_forecast
                ],
                'generated_at': forecast.generated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            result_data.append(data)
        
        # 计算总页数
        total_pages = (total_count + pagesize - 1) // pagesize
        
        return Response({
            'status': 'success',
            'data': result_data,
            'pagination': {
                'total_count': total_count,
                'page': page,
                'pagesize': pagesize,
                'total_pages': total_pages
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"获取销售预估数据失败: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'获取销售预估数据失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def map_currency_rate(currency_rate):
    # 处理字典格式的数据
    if isinstance(currency_rate, dict):
        return {
            'currency': currency_rate.get('currency'),
            'currency_symbol': currency_rate.get('currencySymbol'),
            'currency_name': currency_rate.get('currencyName'),
            'reference_rate': currency_rate.get('referenceRate'),
            'custom_rate': currency_rate.get('customRate'),
            'state': currency_rate.get('state'),
            'month_date': currency_rate.get('monthDate'),
            'last_date': currency_rate.get('lastDate')
        }
    else:
        # 处理对象格式的数据
        return {
            'currency': currency_rate.currency,
            'currency_symbol': currency_rate.currencySymbol,
            'currency_name': currency_rate.currencyName,
            'reference_rate': currency_rate.referenceRate,
            'custom_rate': currency_rate.customRate,
            'state': currency_rate.state,
            'month_date': currency_rate.monthDate,
            'last_date': currency_rate.lastDate
        }



# 同步汇率数据
@api_view(['POST'])
@permission_classes([AllowAny])
def sync_currency_rates(request):
    """
    同步汇率数据
    """
    # 初始化日志记录器
    logger = logging.getLogger(__name__)
    logger.info("开始同步汇率数据")
    # 创建同步日志记录
    sync_log = SyncLog.objects.create(
        sync_type='currency_rates',
        status='running',
        total_count=0,
        success_count=0,
        failed_count=0,
    )

    # 验证请求参数
    serializer = CurrencyRateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        logger.error(f"请求参数验证失败: {serializer.errors}")
        return Response({
            'status': 'failed',
            'message': '请求参数无效',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 初始化api客户端
        client = GerpgoAPIClient(
            appId=settings.GERPGO_APP_ID,
            appKey=settings.GERPGO_APP_KEY,
            base_url=settings.GERPGO_API_BASE_URL
        )

        # 获取分页参数
        page = serializer.validated_data.get('page',1)
        pagesize = serializer.validated_data.get('pagesize',500)

        # 初始化分页参数
        total_pages = 1
        success_count = 0
        error_count = 0
        error_details = []
        
        while page <= total_pages:
            logger.info(f"获取第{page}页产品数据，每页{pagesize}条")
            # 获取产品列表
            success,data = client.get_currency_rate(
                page = page,
                pagesize = pagesize
            )

            if not success:
                error_msg = f"获取汇率失败“{response.get('error', '未知错误')}"
                logger.error(error_msg)
                error_count += 1
                break

            # 处理返回数据
            if data and 'data' in data:
                total_pages = math.ceil(data['data'].get('total', 0) / pagesize)
                # 处理返回数据
                for row in data['data'].get('rows',[]):
                    try:
                        # 解析数据
                        mapped_data = map_currency_rate(row)
                        # 使用update_or_create更新或创建数据
                        updated,created = CurrencyRate.objects.update_or_create(
                            currency = mapped_data['currency'],
                            month_date = mapped_data['month_date'],
                            defaults = mapped_data
                        )
                        if created:
                            logger.info(f"创建新纪录：{mapped_data['month_date']}-{mapped_data['currency']}")
                        else:
                            logger.info(f"更新记录：{mapped_data['month_date']}-{mapped_data['currency']}")
                    except Exception as e:
                        error_msg = f"处理汇率数据异常：{str(e)}"
                        logger.error(error_msg)
                        error_count += 1
                        error_details.append(error_msg)
            else:
                break
            page+=1

        # 更新同步日志
        sync_log.status = 'success' if error_count == 0 else 'partial_success'
        sync_log.end_time = timezone.now()
        sync_log.success_count = success_count
        sync_log.failed_count = error_count
        sync_log.error_message = json.dumps({
        'error_details': error_details,
        'total_processed': success_count + error_count
        }) # 记录错误详情
        sync_log.save()

        # 返回成功相应
        return Response({
            'status': 'success',
            'message': '数据同步完成',
            'sync_log_id': sync_log.id,
            'total_processed': success_count + error_count,
            'success_count': success_count,
            'failed_count': error_count
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"数据同步异常:{str(e)}")
        
        # 更新同步日志为失败
        sync_log.status = 'failed'
        sync_log.end_time = timezone.now()
        sync_log.failed_count = error_count
        sync_log.error_message = json.dumps({
        'error_details': [str(e)],
        'total_processed': success_count + error_count
        }) # 记录异常信息
        sync_log.save() # 保存同步日志到数据库

        # 返回失败相应
        return Response({
            'status': 'failed',
            'message': '数据同步过程中发生异常',
            'sync_log_id': sync_log.id,
            'total_processed': success_count + error_count,
            'failed_count': error_count,
            'error_details': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)