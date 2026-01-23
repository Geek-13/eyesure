"""
序列化器定义
"""
from rest_framework import serializers
from datetime import datetime
# 在导入语句中添加AdsSbCreative模型
from .models import (Product,SyncLog,Market,SellerMarketplace,AdsSpKeyword,
                        AdsSpTarget,AdsSpPlacement,AdsSpSearchTerms,AdsSbKeyword,
                        AdsSbCampaign, AdsSbCreative, AdsSbTargeting,AdsSbPlacement, 
                        AdsSbSearchTerms,AdsSdCampaign,AdsSdProduct,InventoryStorageLedger
                        ,InventoryStorageLedgerDetail,Transaction,TrafficAnalysis,FBAInventory,
                        SalesForecast)


class ProductSerializer(serializers.ModelSerializer):
    """产品序列化器"""
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'barcode', 'category', 'brand', 'description',
            'price', 'cost', 'weight', 'length', 'width', 'height',
            'images', 'attributes', 'status', 'created_at', 'updated_at',
            'sync_status', 'last_sync_time', 'gerpgo_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SyncLogSerializer(serializers.ModelSerializer):
    """同步日志序列化器"""
    sync_type_display = serializers.ReadOnlyField(source='get_sync_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = SyncLog
        fields = [
            'id', 'sync_type', 'sync_type_display', 'start_time', 'end_time',
            'status', 'status_display', 'total_count', 'success_count',
            'failed_count', 'error_message'
        ]
        read_only_fields = ['id', 'start_time', 'end_time']


class SyncRequestSerializer(serializers.Serializer):
    """同步请求序列化器"""
    # 驼峰命名方式（beginDate, endDate）
    beginDate = serializers.DateTimeField(required=False)
    endDate = serializers.DateTimeField(required=False)
    forceFullSync = serializers.BooleanField(default=False, required=False) # 是否强制全量同步
    pageSize = serializers.IntegerField(default=100, min_value=1, max_value=1000, required=False, source='page_size') # 分页大小
    
    # 下划线命名方式（start_date, end_date）
    start_date = serializers.DateTimeField(required=False, source='beginDate')
    end_date = serializers.DateTimeField(required=False, source='endDate')
    force_full_sync = serializers.BooleanField(default=False) # 是否强制全量同步
    page = serializers.IntegerField(default=1, min_value=1) # 分页页码
    page_size = serializers.IntegerField(default=100, min_value=1, max_value=1000) # 分页大小
    warehouse_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="仓库ID列表"
    )


class StatusSerializer(serializers.Serializer):
    """状态信息序列化器"""
    status = serializers.CharField(max_length=20)
    message = serializers.CharField(max_length=255)
    timestamp = serializers.DateTimeField()
    version = serializers.CharField(max_length=20)
    api_connections = serializers.DictField()


class MarketSerializer(serializers.ModelSerializer):
    """市场信息序列化器"""
    class Meta:
        model = Market
        fields = [
            'id', 'market_id', 'market', 'market_name', 'area_id', 'area_name',
            'country_id', 'server_id', 'server_name', 'warehouse_id', 'warehouse_name',
            'session', 'ads_state', 'api_state', 'state', 'market_state', 'model',
            'auth_type', 'disable_sub_account', 'subscript_offer_change', 'store',
            'account', 'seller_id', 'record_date', 'add_date', 'total_auth_email_num',
            'normal_auth_email_num', 'invalid_auth_email_num', 'authorized_market_ids',
            'authorized_country_ids', 'attribute_list', 'created_at', 'updated_at',
            'sync_status', 'last_sync_time', 'gerpgo_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class SellerMarketplaceSerializer(serializers.ModelSerializer):
    """卖家市场关联序列化器"""
    class Meta:
        model = SellerMarketplace
        fields = [
            'id', 'area_id', 'seller_id', 'area_name', 'created_at', 'updated_at',
            'sync_status', 'last_sync_time', 'gerpgo_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SPADDataRequestSerializer(serializers.Serializer):
    """SPAD数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )



class SPKWDataRequestSerializer(serializers.Serializer):
    """SPKW数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )


class AdsSpKeywordSerializer(serializers.ModelSerializer):
    """SP广告关键词数据序列化器"""
    class Meta:
        model = AdsSpKeyword
        fields = [
            'id', 'trace_id', 'market_id', 'keyword_id', 'hash',
            'keyword_text', 'match_type', 'bid',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'serving_status', 'state',
            'impressions', 'clicks', 'cost',
            'ads_sales', 'ads_product_sales', 'other_product_sales',
            'ads_orders', 'ads_product_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas',
            'create_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# 添加SBKW数据请求序列化器
class SBKWDataRequestSerializer(serializers.Serializer):
    """SBKW数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )

# 添加SB广告关键词数据模型序列化器
class AdsSbKeywordSerializer(serializers.ModelSerializer):
    """SB广告关键词数据序列化器"""
    class Meta:
        model = AdsSbKeyword
        fields = [
            'id', 'trace_id', 'market_id', 'keyword_id', 'hash',
            'keyword_text', 'match_type', 'bid',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'state', 'ads_type',
            'impressions', 'view_impressions', 'clicks', 'page_views', 'cost',
            'ads_sales', 'ads_product_sales', 'other_product_sales', 'new_buyer_sales',
            'ads_orders', 'ads_product_orders', 'new_buyer_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas', 'cpv', 'new_buyer_order_ratio', 'new_buyer_sale_ratio',
            'create_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class SBCampainDataRequestSerializer(serializers.Serializer):
    """SBCampain数据同步请求序列化器"""
    marketIds = serializers.ListField(child=serializers.IntegerField(), required=False, help_text="市场ID列表（驼峰命名）")
    count = serializers.IntegerField(required=False, min_value=1, max_value=100, default=100)
    startDataDate = serializers.DateField(required=False, help_text="开始日期（驼峰命名）")
    endDataDate = serializers.DateField(required=False, help_text="结束日期（驼峰命名）")
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )


class AdsSbCampaignSerializer(serializers.ModelSerializer):
    """SBCampain数据响应序列化器"""
    class Meta:
        model = AdsSbCampaign
        fields = '__all__'


# 在文件末尾添加以下代码
class SBCreativeDataRequestSerializer(serializers.Serializer):
    """SB创意数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )


class AdsSbCreativeSerializer(serializers.ModelSerializer):
    """SB广告创意数据序列化器"""
    class Meta:
        model = AdsSbCreative
        fields = [
            'id', 'trace_id', 'market_id', 'creative_id', 'hash',
            'asin', 'skus', 'title', 'brand',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'serving_status', 'state',
            'impressions', 'clicks', 'cost',
            'ads_sales', 'ads_product_sales', 'other_product_sales',
            'ads_orders', 'ads_product_orders', 'other_product_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas',
            'new_buyer_order_ratio', 'unit_session_percentage',
            'create_date', 'start_date', 'end_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# 在文件末尾添加以下代码
class SPTargetDataRequestSerializer(serializers.Serializer):
    """SPTarget数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )

# 在SPTargetDataRequestSerializer后添加以下代码
class SPPlacementDataRequestSerializer(serializers.Serializer):
    """SPPlacement数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )

# 同时添加对应的模型序列化器
class AdsSpPlacementSerializer(serializers.ModelSerializer):
    """SP广告展示位置数据序列化器"""
    class Meta:
        model = AdsSpPlacement
        fields = [
            'id', 'trace_id', 'market_id', 'placement_id', 'hash',
            'placement', 'targeting_type',
            'campaign_id', 'campaign_name', 'campaign_type',
            'portfolio_id', 'portfolio_name', 'daily_budget',
            'serving_status', 'state',
            'impressions', 'clicks', 'cost',
            'ads_sales', 'ads_product_sales', 'other_product_sales',
            'ads_orders', 'ads_product_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas',
            'create_date', 'start_date', 'end_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdsSpTargetSerializer(serializers.ModelSerializer):
    """SP广告目标投放数据序列化器"""
    class Meta:
        model = AdsSpTarget
        fields = [
            'id', 'trace_id', 'market_id', 'target_id', 'hash',
            'targeting_text', 'targeting_type',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'serving_status', 'state',
            'impressions', 'clicks', 'cost',
            'ads_sales', 'ads_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas',
            'create_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# 在文件末尾添加以下代码
class SPSearchTermsDataRequestSerializer(serializers.Serializer):
    """SP搜索词数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )

# 添加SP搜索词数据模型序列化器
class AdsSpSearchTermsSerializer(serializers.ModelSerializer):
    """SP广告搜索词数据序列化器"""
    class Meta:
        model = AdsSpSearchTerms
        fields = [
            'id', 'trace_id', 'market_id', 'keyword_id', 'hash',
            'keyword_text', 'match_type', 'query',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'serving_status', 'state',
            'impressions', 'clicks', 'cost',
            'ads_sales', 'ads_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas',
            'create_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



# 添加SBTargeting数据请求序列化器
class SBTargetingDataRequestSerializer(serializers.Serializer):
    """SB目标投放数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )

# 添加SB目标投放数据模型序列化器
class AdsSbTargetingSerializer(serializers.ModelSerializer):
    """SB广告目标投放数据序列化器"""
    class Meta:
        model = AdsSbTargeting
        fields = [
            'id', 'trace_id', 'market_id', 'targeting_id', 'hash',
            'targeting_text', 'targeting_type', 'bid',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'state', 'serving_status', 'ads_type',
            'impressions', 'view_impressions', 'clicks', 'page_views', 'cost',
            'ads_sales', 'ads_product_sales', 'other_product_sales', 'new_buyer_sales',
            'ads_orders', 'ads_product_orders', 'new_buyer_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas', 'cpv',
            'new_buyer_order_ratio', 'new_buyer_sale_ratio',
            'create_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# 在文件末尾添加以下代码
class SBPlacementDataRequestSerializer(serializers.Serializer):
    """SB展示位置数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )

class AdsSbPlacementSerializer(serializers.ModelSerializer):
    """SB广告展示位置数据序列化器"""
    class Meta:
        model = AdsSbPlacement
        fields = [
            'id', 'trace_id', 'market_id', 'placement_id', 'hash',
            'placement', 'targeting_type', 'budget_type', 'budget',
            'campaign_id', 'campaign_name', 'portfolio_id', 'portfolio_name',
            'state', 'ads_type', 'serving_status',
            'impressions', 'view_impressions', 'clicks', 'page_views', 'cost',
            'ads_sales', 'ads_product_sales', 'other_product_sales', 'new_buyer_sales',
            'ads_orders', 'ads_product_orders', 'new_buyer_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas', 'cpv',
            'new_buyer_order_ratio', 'new_buyer_sale_ratio',
            'create_date', 'start_date', 'end_date', 'report_date', 'asins',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



# 添加SB搜索词数据请求序列化器
class SBSearchTermsDataRequestSerializer(serializers.Serializer):
    """SB搜索词数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )

# 添加SB搜索词数据模型序列化器
class AdsSbSearchTermsSerializer(serializers.ModelSerializer):
    """SB广告搜索词数据序列化器"""
    class Meta:
        model = AdsSbSearchTerms
        fields = [
            'id', 'trace_id', 'market_id', 'keyword_id', 'hash',
            'keyword_text', 'match_type', 'query',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'serving_status', 'state',
            'impressions', 'view_impressions', 'clicks', 'cost',
            'ads_sales', 'ads_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas', 'cpv',
            'create_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AdsSdCampaignSerializer(serializers.ModelSerializer):
    """SD广告活动数据序列化器"""
    class Meta:
        model = AdsSdCampaign
        fields = [
            'id', 'trace_id', 'market_id', 'campaign_id', 'hash',
            'campaign_name', 'budget_type', 'budget', 'cost_type',
            'serving_status', 'state', 'tactic',
            'portfolio_id', 'portfolio_name',
            'impressions', 'view_impressions', 'clicks', 'page_views', 'cost',
            'ads_sales', 'other_product_sales', 'ads_product_sales',
            'ads_orders', 'ads_product_orders', 'new_buyer_orders', 'new_buyer_sales',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas',
            'new_buyer_order_ratio', 'new_buyer_sale_ratio',
            'create_date', 'start_date', 'end_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']




# 添加SDCampaign数据请求序列化器
class SDSCampaignDataRequestSerializer(serializers.Serializer):
    """SDCampaign数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )


class SDProductDataRequestSerializer(serializers.Serializer):
    """SDProduct数据请求序列化器"""
    marketIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        help_text="市场ID列表（驼峰命名）"
    )
    count = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-100，默认100"
    )
    startDataDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endDataDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    market_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        source='marketIds',
        help_text="市场ID列表（下划线命名）"
    )
    start_data_date = serializers.DateField(
        required=False,
        source='startDataDate',
        help_text="开始日期（下划线命名）"
    )
    end_data_date = serializers.DateField(
        required=False,
        source='endDataDate',
        help_text="结束日期（下划线命名）"
    )


class AdsSdProductSerializer(serializers.ModelSerializer):
    """SD广告产品数据序列化器"""
    class Meta:
        model = AdsSdProduct
        fields = [
            'id', 'trace_id', 'market_id', 'ad_id', 'hash',
            'msku', 'asin',
            'group_id', 'group_name', 'campaign_id', 'campaign_name',
            'portfolio_id', 'portfolio_name',
            'state', 'serving_status', 'cost_type',
            'impressions', 'view_impressions', 'clicks', 'page_views', 'cost',
            'ads_sales', 'ads_product_sales', 'other_product_sales', 'new_buyer_sales',
            'ads_orders', 'ads_product_orders', 'new_buyer_orders',
            'ctr', 'cpc', 'cpa', 'cvr', 'acos', 'roas',
            'new_buyer_order_ratio', 'new_buyer_sale_ratio',
            'create_date', 'report_date',
            'created_at', 'updated_at', 'sync_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# 添加库存分类账数据请求序列化器
class InventoryStorageLedgerRequestSerializer(serializers.Serializer):
    """库存分类账数据请求序列化器"""
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        required=False,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        required=False,
        help_text="每页数量，范围1-1000，默认100"
    )
    reportStartDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    reportEndDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    report_start_date = serializers.DateField(
        required=False,
        source='reportStartDate',
        help_text="开始日期（下划线命名）"
    )
    report_end_date = serializers.DateField(
        required=False,
        source='reportEndDate',
        help_text="结束日期（下划线命名）"
    )

# 添加库存分类账数据模型序列化器
class InventoryStorageLedgerSerializer(serializers.ModelSerializer):
    """库存分类账数据序列化器"""
    class Meta:
        model = InventoryStorageLedger
        fields = [
            # 产品基本信息
            'id', 'country', 'fnsku', 'sku', 'msku', 'asin', 'product_name',
            
            # 仓库信息
            'warehouse_id', 'warehouse_name',
            
            # 数量指标
            'opening_balance', 'receipts', 'shipments', 'returns',
            'adjustments', 'closing_balance', 'available', 'reserved',
            'warehouse_transfer_in_and_out', 'in_transit_between_warehouses',
            'damaged', 'disposed', 'lost', 'found', 'unknown_events', 'other_events',
            
            # 日期信息
            'report_date', 'create_time', 'update_time',
            
            # 系统字段
            'created_at', 'updated_at', 'sync_status', 'last_sync_time', 'gerpgo_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# 添加库存分类账明细数据请求序列化器
class InventoryStorageLedgerDetailRequestSerializer(serializers.Serializer):
    """库存分类账明细数据请求序列化器"""
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        required=False,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        required=False,
        help_text="每页数量，范围1-1000，默认100"
    )
    beginReportDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰命名）"
    )
    endReportDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰命名）"
    )
    # 下划线命名方式支持
    begin_report_date = serializers.DateField(
        required=False,
        source='beginReportDate',
        help_text="开始日期（下划线命名）"
    )
    end_report_date = serializers.DateField(
        required=False,
        source='endReportDate',
        help_text="结束日期（下划线命名）"
    )

# 添加库存分类账明细数据模型序列化器
class InventoryStorageLedgerDetailSerializer(serializers.ModelSerializer):
    """库存分类账明细数据序列化器"""
    class Meta:
        model = InventoryStorageLedgerDetail
        fields = [
            # 产品基本信息
            'id', 'country', 'fnsku', 'sku', 'msku', 'asin', 'sku_name', 'source_msku',
            
            # 仓库信息
            'warehouse_name', 'fulfillment_center', 'disposition',
            
            # 事件信息
            'event_type', 'quantity', 'reason', 'reference_id',
            
            # 日期信息
            'report_date', 'create_time', 'update_time', 'show_detail_button',
            
            # 系统字段
            'created_at', 'updated_at', 'sync_status', 'last_sync_time', 'gerpgo_id', 'gerpgo_data'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']



class TransactionSerializer(serializers.ModelSerializer):
    """交易数据序列化器"""
    class Meta:
        model = Transaction
        fields = [
            # 交易基本信息
            'id', 'type', 'order_id', 'settlement_id', 'description',
            
            # 订单相关信息
            'order_type', 'order_state', 'sale_order_type', 'test_order', 'test_order_name',
            
            # 产品信息
            'product', 'sku', 'origin_sku', 'quantity',
            
            # 市场信息
            'market_id', 'market_name', 'marketplace', 'country_code', 'country_name',
            
            # 地址信息
            'order_city', 'order_postal',
            
            # 金额信息
            'total', 'product_sales', 'shipping_credits', 'gift_wrap_credits', 'promotional_rebates',
            
            # 费用信息
            'selling_fees', 'fba_fees', 'other_transaction_fees', 'regulatory_fee', 'other',
            
            # 税费信息
            'product_sales_tax', 'shipping_credits_tax', 'gift_wrap_credits_tax', 
            'promotional_rebates_tax', 'regulatory_fee_tax', 'marketplace_withheld_tax',
            'tcscgst', 'tcssgst', 'tcsigst',
            
            # 其他信息
            'fee_type', 'tax_collection_model', 'fulfillment', 'points_granted',
            
            # 货币信息
            'currency', 'currency_symbol',
            
            # 日期信息
            'standard_date', 'zero_date', 'market_date', 'create_date', 'update_date',
            
            # 系统字段
            'created_at', 'updated_at', 'sync_status', 'last_sync_time', 'gerpgo_id', 'gerpgo_data'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class TransactionRequestSerializer(serializers.Serializer):
    """交易数据请求序列化器"""
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        required=False,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        required=False,
        help_text="每页数量，范围1-1000，默认100"
    )
    # 驼峰命名格式字段（支持前端直接传递）
    purchaseStartDate = serializers.DateField(
        required=False,
        help_text="开始日期（驼峰格式）"
    )
    purchaseEndDate = serializers.DateField(
        required=False,
        help_text="结束日期（驼峰格式）"
    )
    queryDateType = serializers.IntegerField(
        default=0,
        required=False,
        help_text="查询日期类型，0：市场日期，1：标准日期（驼峰格式）"
    )
    deleteOldData = serializers.BooleanField(
        default=False,
        required=False,
        help_text="是否删除旧数据（驼峰格式）"
    )
    
    # 下划线命名格式字段（确保兼容性）
    purchase_start_date = serializers.DateField(
        required=False,
        help_text="开始日期（下划线格式）"
    )
    purchase_end_date = serializers.DateField(
        required=False,
        help_text="结束日期（下划线格式）"
    )
    query_date_type = serializers.IntegerField(
        default=0,
        required=False,
        help_text="查询日期类型，0：市场日期，1：标准日期（下划线格式）"
    )
    delete_old_data = serializers.BooleanField(
        default=False,
        required=False,
        help_text="是否删除旧数据（下划线格式）"
    )


# 第二处修改：在文件末尾添加TrafficAnalysis序列化器
class TrafficAnalysisSerializer(serializers.ModelSerializer):
    """流量分析数据序列化器"""
    class Meta:
        model = TrafficAnalysis
        fields = [
            # 基础信息
            'id', 'sku', 'asin', 'parent_asin', 'product_name', 'market_name',
            
            # 市场信息
            'market_id', 'marketplace_id', 'country', 'currency',
            
            # 产品分类信息
            'product_group', 'product_category', 'product_subcategory',
            
            # 人员信息
            'operate_by', 'team',
            
            # 流量数据
            'sessions', 'sessions_percentage', 'page_views', 'page_views_percentage',
            'buy_box_percentage', 'units_ordered', 'units_ordered_percentage',
            'ordered_product_sales', 'ordered_product_sales_amount',
            
            # 损失流量数据
            'loss_traffics',
            
            # 时间信息
            'date', 'begin_date', 'end_date',
            
            # 系统字段
            'created_at', 'updated_at', 'sync_status', 'last_sync_time', 'gerpgo_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrafficAnalysisRequestSerializer(serializers.Serializer):
    """流量分析数据请求序列化器"""
    currency = serializers.CharField(
        default='YUAN',
        required=False,
        help_text="货币类型，默认为YUAN"
    )
    beginDate = serializers.DateField(
        required=False,  # 改为非必填
        help_text="开始日期（如果不提供，默认为7天前）"
    )
    endDate = serializers.DateField(
        required=False,  # 改为非必填
        help_text="结束日期（如果不提供，默认为今天）"
    )
    # 添加对下划线命名方式的支持
    start_date = serializers.DateField(
        required=False,
        source='beginDate',
        help_text="开始日期（下划线命名方式，与beginDate同义）"
    )
    end_date = serializers.DateField(
        required=False,
        source='endDate',
        help_text="结束日期（下划线命名方式，与endDate同义）"
    )
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        required=False,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        required=False,
        help_text="每页数量，范围1-1000，默认100"
    )
    viewType = serializers.CharField(
        default='day',
        required=False,
        help_text="视图类型，默认为day"
    )


# FBAInventory序列化器
class FBAInventorySerializer(serializers.ModelSerializer):
    """FBA库存数据序列化器"""
    class Meta:
        model = FBAInventory
        fields = [
            # 产品基本信息
            'id', 'msku', 'asin', 'fnsku', 'product_name',
            
            # 仓库信息
            'warehouse_id', 'warehouse_name', 'warehouse_country',
            
            # 库存数量信息
            'fulfillable_quantity', 'reserved_quantity', 'total_quantity',
            
            # 预留库存明细
            'reserved_transit', 'reserved_consumer_orders', 
            'reserved_pending_transfers', 'reserved_research',
            
            # 入库信息
            'inbound_working_quantity', 'inbound_shipped_quantity', 
            'inbound_receiving_quantity',
            
            # ERP入库信息
            'erp_inbound_quantity', 'erp_inbound_status',
            
            # 库存年龄信息
            'aging_0_30', 'aging_31_90', 'aging_91_180', 'aging_181_365', 'aging_365_plus',
            
            # 其他数量信息
            'unfulfillable_quantity', 'removals_in_process', 'recycle_bin_quantity',
            
            # 销售和周转信息
            'turnover_days', 'sales_velocity',
            
            # 状态信息
            'status', 'condition', 'listing_status',
            
            # 时间信息
            'last_updated', 'record_date',
            
            # 管理信息
            'operate_by', 'team',
            
            # 国家列表信息
            'countries_of_operation',
            
            # 系统字段
            'created_at', 'updated_at', 'sync_status', 'last_sync_time', 'gerpgo_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FBAInventorySyncRequestSerializer(serializers.Serializer):
    """FBA库存数据同步请求序列化器"""
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        required=False,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        required=False,
        help_text="每页数量，范围1-1000，默认100"
    )
    warehouse_country = serializers.CharField(
        required=False,
        help_text="仓库国家筛选，可选"
    )
    sku = serializers.CharField(
        required=False,
        help_text="SKU筛选，可选"
    )
    last_updated_after = serializers.DateTimeField(
        required=False,
        help_text="最后更新时间筛选，可选"
    )

class MonStorageFeeRequestSerializer(serializers.Serializer):
    """月度仓储费数据请求序列化器"""
    page = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=True,
        help_text="每页数量，范围1-1000，默认100"
    )

    year = serializers.IntegerField(
        required=False,
        default=datetime.now().year,
        min_value=2020,
        max_value=datetime.now().year,
        help_text="年份筛选，可选"
    )

    month = serializers.IntegerField(
        required=False,
        default=datetime.now().month,
        min_value=1,
        max_value=12,
        help_text="月份筛选，可选"
    )


# 利润分析请求参数序列化器
class ProfitAnalysisRequestSerializer(serializers.Serializer):
    """利润分析数据请求序列化器"""
    page = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
        help_text="每页数量，范围1-1000，默认100"
    )
    type = serializers.CharField(
        default='MSKU',
        required=False,
        help_text="视图类型，默认为MSKU"
    )
    showCurrencyType = serializers.CharField(
        default='YUAN',
        required=False,
        help_text="货币类型，默认为YUAN"
    )
    beginDate = serializers.DateField(
        required=False,
        help_text="开始日期"
    )
    endDate = serializers.DateField(
        required=False,
        help_text="结束日期"
    )
    # 添加对下划线命名方式的支持
    start_date = serializers.DateField(
        required=False,
        source='beginDate',
        help_text="开始日期（下划线命名方式，与beginDate同义）"
    )
    end_date = serializers.DateField(
        required=False,
        source='endDate',
        help_text="结束日期（下划线命名方式，与endDate同义）"
    )
    pageSize = serializers.IntegerField(
        source='pagesize',
        default=100,
        min_value=1,
        max_value=1000,
        required=False,
        help_text="每页数量，范围1-1000，默认100"
    )


# 销售预估请求序列化器
class SalesForecastRequestSerializer(serializers.Serializer):
    market_ids = serializers.ListField(required=False, child=serializers.CharField())
    market_names = serializers.ListField(required=False, child=serializers.CharField())
    asins = serializers.ListField(required=False, child=serializers.CharField())
    forecast_method = serializers.CharField(required=False, default='moving_average')
    lookback_period = serializers.IntegerField(required=False, default=90)  # 回看天数
    forecast_months = serializers.IntegerField(required=False, default=12)  # 预估月数
    confidence_level = serializers.DecimalField(required=False, max_digits=3, decimal_places=2, default=0.95)


class CurrencyRateRequestSerializer(serializers.Serializer):
    """汇率数据请求序列化器"""
    page = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text="页码，从1开始"
    )
    pagesize = serializers.IntegerField(
        min_value=1,
        max_value=500,
        required=False,
        help_text="每页数量，范围1-500，默认500"
    )




# 历史销售数据导入请求序列化器
class HistoricalSalesDataImportSerializer(serializers.Serializer):
    """历史销售数据导入请求序列化器"""
    market_name = serializers.CharField(required=True, help_text="市场名称")
    asin = serializers.CharField(required=True, help_text="ASIN")
    sales_data = serializers.ListField(
        child=serializers.DictField(
            child=serializers.Field(),
            help_text="单条销售数据，包含date、units_sold、sales_amount等字段"
        ),
        help_text="销售数据列表"
    )
    replace_existing = serializers.BooleanField(default=False, help_text="是否替换现有数据")
