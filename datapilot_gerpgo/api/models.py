"""
数据模型定义
"""
from enum import auto
from django.db import models
from django.utils import timezone

# 基础模型，包含通用字段
class BaseModel(models.Model):
    """基础模型，包含通用字段"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待同步'),
            ('syncing', '同步中'),
            ('success', '同步成功'),
            ('failed', '同步失败'),
        ],
        default='pending',
        verbose_name='同步状态'
    )
    last_sync_time = models.DateTimeField(null=True, blank=True, verbose_name='最后同步时间')
    sync_message = models.TextField(blank=True, null=True, verbose_name='同步消息')
    gerpgo_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Gerpgo ID')
    gerpgo_data = models.JSONField(blank=True, null=True, verbose_name='原始数据')
    
    class Meta:
        abstract = True
        ordering = ['-updated_at']


# 同步日志模型
class SyncLog(models.Model):
    """同步日志模型"""
    sync_type = models.CharField(
        max_length=50,
        choices=[
            ('products', '产品'),
            ('inventory', '库存'),
            ('all', '全部'),
        ],
        verbose_name='同步类型'
    )
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    status = models.CharField(
        max_length=20,
        choices=[
            ('running', '运行中'),
            ('success', '成功'),
            ('failed', '失败'),
        ],
        default='running',
        verbose_name='状态'
    )
    total_count = models.IntegerField(default=0, verbose_name='总数量')
    success_count = models.IntegerField(default=0, verbose_name='成功数量')
    failed_count = models.IntegerField(default=0, verbose_name='失败数量')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    
    def __str__(self):
        return f'{self.get_sync_type_display()} 同步 - {self.get_status_display()}'
    
    class Meta:
        verbose_name = '同步日志'
        verbose_name_plural = '同步日志列表'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['sync_type']),
            models.Index(fields=['status']),
            models.Index(fields=['start_time']),
        ]


# 产品模型
class Product(BaseModel):
    """产品模型"""
    market_name = models.CharField(max_length=100, verbose_name='市场名称',default='')
    market_id = models.IntegerField(verbose_name='市场ID',default=0)
    sku = models.CharField(max_length=100, verbose_name='SKU',default='')
    asin = models.CharField(max_length=100, verbose_name='ASIN',null=True)
    fnsku = models.CharField(max_length=100, blank=True, null=True, verbose_name='FNSKU')
    product_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='产品名称')
    category_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='分类名称')
    storage_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='仓储类型编码')
    storage_type_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='仓储类型名称')
    fulfillment = models.CharField(max_length=100, blank=True, null=True, verbose_name='配送渠道')
    sale_state = models.CharField(max_length=100, blank=True, null=True, verbose_name='销售状态')
    sale_manager_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='销售负责人')
    product_manager_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='产品负责人')
    first_sale_date = models.DateField(blank=True, null=True, verbose_name='首次销售日期')
    package_length = models.FloatField(blank=True, null=True, verbose_name='包装长度')
    package_width = models.FloatField(blank=True, null=True, verbose_name='包装宽度')
    package_height = models.FloatField(blank=True, null=True, verbose_name='包装高度')
    package_weight = models.FloatField(blank=True, null=True, verbose_name='包装重量')
    product_length = models.FloatField(blank=True, null=True, verbose_name='产品长度')
    product_width = models.FloatField(blank=True, null=True, verbose_name='产品宽度')
    product_height = models.FloatField(blank=True, null=True, verbose_name='产品高度')
    product_weight = models.FloatField(blank=True, null=True, verbose_name='产品重量')
    item_condition = models.CharField(max_length=100, blank=True, null=True, verbose_name='商品状态')
    spu = models.CharField(max_length=100, blank=True, null=True, verbose_name='SPU')
    spu_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='SPU名称')

    status = models.CharField(
        max_length=20,
        choices=[
            ('active', '活跃'),
            ('inactive', '非活跃'),
            ('draft', '草稿'),
        ],
        default='active',
        verbose_name='状态'
    )
    
    def __str__(self):
        return f'{self.market_name} ({self.sku})'
    
    class Meta:
        verbose_name = '产品'
        verbose_name_plural = '产品列表'
        indexes = [
            models.Index(fields=['market_name']),
            models.Index(fields=['sku']),
            models.Index(fields=['asin'])
        ]
        ordering = ['market_name', 'sku']
        unique_together = ['market_name', 'sku','asin','fnsku','item_condition','sale_state']


# 市场模型
class Market(BaseModel):
    """市场信息模型"""
    market_id = models.IntegerField(verbose_name='市场ID', unique=True)
    area_name = models.CharField(max_length=50, verbose_name='区域名称', blank=True, null=True)
    market = models.CharField(max_length=50, verbose_name='市场代码', blank=True, null=True)
    market_name = models.CharField(max_length=100, verbose_name='市场名称', blank=True, null=True)
    area_id = models.IntegerField(verbose_name='区域ID', default=0)
    store = models.CharField(max_length=100, verbose_name='店铺', blank=True, null=True)
    country_id = models.IntegerField(verbose_name='国家ID', default=0)
    country_code = models.CharField(max_length=10, verbose_name='国家代码', blank=True, null=True)
    country_name = models.CharField(max_length=100, verbose_name='国家名称', blank=True, null=True)
    ads_state = models.CharField(max_length=50, verbose_name='广告状态', blank=True, null=True)
    api_state = models.CharField(max_length=50, verbose_name='API状态', blank=True, null=True)
    state = models.IntegerField(verbose_name='状态', default=0)
    market_state = models.IntegerField(verbose_name='市场状态', default=0)
    disable_sub_account = models.IntegerField(verbose_name='禁用子账户', default=0, blank=True, null=True)
    account = models.CharField(max_length=100, verbose_name='账户', blank=True, null=True)
    seller_id = models.CharField(max_length=100, verbose_name='卖家ID', blank=True, null=True)
    record_date = models.DateTimeField(verbose_name='记录日期', blank=True, null=True)

    
    def __str__(self):
        return f'{self.market} ({self.market_name})'
    
    class Meta:
        verbose_name = '市场信息'
        verbose_name_plural = '市场信息列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['seller_id']),
            models.Index(fields=['record_date']),
        ]
        unique_together = ('market_id','seller_id','record_date')  # 添加唯一约束元组


# SellerMarketplace模型修改
class SellerMarketplace(BaseModel):
    """卖家市场关联模型"""
    area_id = models.IntegerField(verbose_name='区域ID')
    seller_id = models.CharField(max_length=100, verbose_name='卖家ID')
    area_name = models.CharField(max_length=50, verbose_name='区域名称', blank=True, null=True)
    
    def __str__(self):
        return f'Seller: {self.seller_id} - Area: {self.area_name}'
    
    class Meta:
        verbose_name = '卖家市场关联'
        verbose_name_plural = '卖家市场关联列表'
        indexes = [
            models.Index(fields=['seller_id']),
            models.Index(fields=['area_id']),
        ]
        unique_together = ('seller_id', 'area_id')  # 添加联合唯一约束


# FBA库存模型
class Inventory(BaseModel):
    """FBA库存模型"""
    snapshot_date = models.DateTimeField(verbose_name='快照日期', default=timezone.now)
    market_place = models.CharField(max_length=50, verbose_name='市场', blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name='sku', blank=True, null=True)
    fnsku = models.CharField(max_length=100, blank=True, null=True, verbose_name='FNSKU')
    asin = models.CharField(max_length=50, blank=True, null=True, verbose_name='ASIN')
    product_name = models.CharField(max_length=255, verbose_name='产品名称', blank=True, null=True)
    condition = models.CharField(max_length=50, blank=True, null=True, verbose_name='产品状态')
    available_quantity = models.IntegerField(verbose_name='可用数量', default=0)
    qty_with_removals_in_progress = models.IntegerField(verbose_name='待移除数量', default=0)
    inv_age_0_to_90_days = models.IntegerField(verbose_name='0-90天库存', default=0)
    inv_age_91_to_180_days = models.IntegerField(verbose_name='91-180天库存', default=0)
    inv_age_181_to_270_days = models.IntegerField(verbose_name='181-270天库存', default=0)
    inv_age_271_to_365_days = models.IntegerField(verbose_name='271-365天库存', default=0)
    inv_age_365_plus_days = models.IntegerField(verbose_name='365天以上库存', default=0)
    qty_to_be_charged_ltsf6mo = models.IntegerField(verbose_name='6个月内待计费数量', default=0,blank=True, null=True)
    qty_predicted_to_be_charged_ltsf6mo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='6个月内预测计费数量', default=0)
    qty_to_be_charged_ltsf12mo = models.IntegerField(verbose_name='12个月内待计费数量', default=0,blank=True, null=True)
    qty_predicted_to_be_charged_ltsf12mo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='12个月内预测计费数量', default=0)
    units_shipped_last_7_days = models.IntegerField(default=0, verbose_name='近7天发货量')
    units_shipped_last_30_days = models.IntegerField(default=0, verbose_name='近30天发货量') 
    units_shipped_last_60_days = models.IntegerField(default=0, verbose_name='近60天发货量')
    units_shipped_last_90_days = models.IntegerField(default=0, verbose_name='近90天发货量')
    alert = models.CharField(max_length=255, blank=True, null=True, verbose_name='预警信息')
    your_price = models.CharField(max_length=255, blank=True, null=True, verbose_name='您的价格')
    sales_price = models.CharField(max_length=255, blank=True, null=True, verbose_name='促销价格')
    lowest_price_new = models.CharField(max_length=255, blank=True, null=True, verbose_name='新的最低价格')
    lowest_price_used = models.CharField(max_length=255, blank=True, null=True, verbose_name='已用最低价格')
    recommended_action = models.CharField(max_length=255, blank=True, null=True, verbose_name='推荐操作')
    healthy_inventory_level = models.IntegerField(blank=True, null=True, verbose_name='健康库存水平')
    recommended_sales_price = models.CharField(max_length=255, blank=True, null=True, verbose_name='推荐促销价')
    recommended_sale_duration = models.CharField(max_length=255, blank=True, null=True, verbose_name='推荐促销天数')
    recommended_removal_qty = models.CharField(max_length=255, blank=True, null=True, verbose_name='推荐移除数量')
    removal_cost_savings = models.CharField(max_length=255, blank=True, null=True, verbose_name='移除成本节省')
    sell_through = models.CharField(max_length=255, blank=True, null=True, verbose_name='售出率')
    item_volume = models.CharField(max_length=255, blank=True, null=True, verbose_name='商品体积')
    cubic_feet = models.CharField(max_length=255, blank=True, null=True, verbose_name='体积计量单位')
    storage_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='仓储类型')
    market_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='市场')
    estimated_storage_cost = models.CharField(max_length=255, blank=True, null=True, verbose_name='预估仓储费')
    create_date = models.DateTimeField(verbose_name='创建日期', default=timezone.now)
    update_date = models.DateTimeField(verbose_name='更新日期', default=timezone.now)
    warehouse_id = models.IntegerField(verbose_name='仓库ID', default=0)
    warehouse_name = models.CharField(max_length=100, verbose_name='仓库名称', blank=True, default='')
    inv_age_0_to_30_days = models.IntegerField(verbose_name='0-30天库存', default=0)
    inv_age_31_to_60_days = models.IntegerField(verbose_name='31-60天库存', default=0)
    inv_age_61_to_90_days = models.IntegerField(verbose_name='61-90天库存', default=0)
    inv_age_271_to_330_days = models.IntegerField(verbose_name='271-330天库存', default=0)
    inv_age_331_to_365_days = models.IntegerField(verbose_name='331-365天库存', default=0)


    def __str__(self):
        return f'{self.product_name} ({self.sku})'
    
    class Meta:
        verbose_name = '库存'
        verbose_name_plural = '库存列表'
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['product_name']),
            models.Index(fields=['warehouse_id']),
        ]
        unique_together = ('snapshot_date', 'warehouse_name', 'market_place','fnsku','condition','sku','asin')


# 广告产品数据模型
class AdsSpProduct(BaseModel):
    """SP广告产品数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID', blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    ad_id = models.CharField(max_length=100, verbose_name='广告商品ID', blank=True, null=True)
    group_targeting_type = models.IntegerField(verbose_name='投放类型', blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name='MSKU', blank=True, null=True)
    asin = models.CharField(max_length=100, verbose_name='ASIN', blank=True, null=True)
    state = models.CharField(max_length=100, verbose_name='广告活动状态', blank=True, null=True)
    serving_status = models.CharField(max_length=100, verbose_name='服务状态', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告商品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告商品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他商品销售额', blank=True, null=True)
    
    def __str__(self):
        return f'({self.market_id}) - {self.portfolio_name}'
    
    class Meta:
        verbose_name = 'SP广告产品数据'
        verbose_name_plural = 'SP广告产品数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['msku']),
            models.Index(fields=['asin']),
            models.Index(fields=['campaign_id']),
            models.Index(fields=['portfolio_id']),
            models.Index(fields=['group_id']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'ad_id', 'create_date','campaign_id','group_id','msku','asin')  # 确保数据唯一性


# 广告关键词数据模型
class AdsSpKeyword(BaseModel):
    """SP广告关键词数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID', blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    keyword_id = models.CharField(max_length=100, verbose_name='广告关键词ID', blank=True, null=True)
    keyword_text = models.CharField(max_length=255, verbose_name='广告关键词文本', blank=True, null=True)
    match_type = models.CharField(max_length=100, verbose_name='匹配类型', blank=True, null=True)
    bid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='竞价', blank=True, null=True)
    serving_status = models.CharField(max_length=100, verbose_name='服务状态', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告商品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告商品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他商品销售额', blank=True, null=True)
    
    
    def __str__(self):
        return f'{self.keyword_text} ({self.campaign_name})'
    
    class Meta:
        verbose_name = 'SP广告关键词数据'
        verbose_name_plural = 'SP广告关键词数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['keyword_text']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'create_date','campaign_id','group_id','match_type','keyword_id')  # 确保数据唯一性


# 目标投放数据模型
class AdsSpTarget(BaseModel):
    """SP广告目标投放数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID', blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    target_id = models.CharField(max_length=100, verbose_name='广告目标ID', blank=True, null=True)
    targeting_text = models.CharField(max_length=255, verbose_name='广告目标文本', blank=True, null=True)
    targeting_type = models.CharField(max_length=100, verbose_name='广告目标类型', blank=True, null=True)
    query = models.CharField(max_length=255, verbose_name='广告查询', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now)

    
    def __str__(self):
        return f'{self.targeting_text} ({self.campaign_name})'
    
    class Meta:
        verbose_name = 'SP广告目标投放数据'
        verbose_name_plural = 'SP广告目标投放数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['target_id']),
            models.Index(fields=['portfolio_id']),
            models.Index(fields=['campaign_id']),
            models.Index(fields=['group_id']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'target_id', 'create_date', 'campaign_id', 'group_id','targeting_type','query')  # 确保数据唯一性


# 在文件末尾添加以下代码
class AdsSpPlacement(BaseModel):
    """SP广告展示位置数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    campaign_type = models.CharField(max_length=100, verbose_name='广告活动类型', blank=True, null=True)
    targeting_type = models.CharField(max_length=100, verbose_name='广告目标类型', blank=True, null=True)
    state = models.CharField(max_length=100, verbose_name='广告状态', blank=True, null=True)
    serving_status = models.CharField(max_length=100, verbose_name='广告投放状态', blank=True, null=True)
    daily_budget = models.CharField(max_length=255, verbose_name='每日预算', blank=True, null=True)
    start_date = models.DateTimeField(verbose_name='开始日期', default=timezone.now,blank=True, null=True)
    end_date = models.DateTimeField(verbose_name='结束日期', default=timezone.now,blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)
    placement = models.CharField(max_length=100, verbose_name='广告展示位置', blank=True, null=True)
    bid_strategy = models.CharField(max_length=100, verbose_name='广告竞价策略', blank=True, null=True)
    bid_strategy_name = models.CharField(max_length=100, verbose_name='广告竞价策略名称', blank=True, null=True)
    rule_roas = models.CharField(max_length=255, verbose_name='广告规则ROAS', blank=True, null=True)
    bid_adjustment = models.CharField(max_length=255, verbose_name='广告竞价调整', blank=True, null=True)
    bid_adjustment_name = models.CharField(max_length=100, verbose_name='广告竞价调整(带单位)', blank=True, null=True)
    bidding = models.CharField(max_length=255, verbose_name='原始竞价策略字段', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告产品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告产品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他产品销售额', blank=True, null=True)
    
    
    def __str__(self):
        return f'{self.placement} ({self.campaign_name})'
    
    class Meta:
        verbose_name = 'SP广告展示位置数据'
        verbose_name_plural = 'SP广告展示位置数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['create_date']),
            models.Index(fields=['placement']),
        ]
        unique_together = ('market_id', 'create_date', 'campaign_id', 'placement')  # 确保数据唯一性


# 在文件末尾添加以下代码
class AdsSpSearchTerms(BaseModel):
    """SP广告搜索词数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    keyword_id = models.CharField(max_length=100, verbose_name='关键词ID', blank=True, null=True)
    keyword_text = models.CharField(max_length=255, verbose_name='关键词文本', blank=True, null=True)
    query = models.CharField(max_length=255, verbose_name='查询', blank=True, null=True)
    match_type = models.IntegerField(verbose_name='匹配类型', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)
    
    def __str__(self):
        return f'{self.keyword_text} ({self.campaign_name})'
    
    class Meta:
        verbose_name = 'SP广告搜索词数据'
        verbose_name_plural = 'SP广告搜索词数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'create_date', 'campaign_id', 'group_id', 'keyword_id','match_type','query')  # 确保数据唯一性


# 在文件末尾添加以下代码
class AdsSbKeyword(BaseModel):
    """SB广告关键词数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    ads_type = models.CharField(max_length=20, verbose_name='广告类型', default='SB')
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    keyword_id = models.CharField(max_length=100, verbose_name='关键词ID', blank=True, null=True)
    keyword_text = models.CharField(max_length=255, verbose_name='关键词文本', blank=True, null=True)
    match_type = models.IntegerField(verbose_name='匹配类型', blank=True, null=True)
    state = models.CharField(max_length=20, verbose_name='状态', blank=True, null=True)
    bid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='出价', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告商品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告商品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他商品销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    new_buyer_orders = models.IntegerField(verbose_name='新买家订单量', blank=True, null=True)
    new_buyer_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='新买家销售额', blank=True, null=True)
    page_views = models.IntegerField(verbose_name='页面浏览量', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)

    
    def __str__(self):
        return f'{self.keyword_text} ({self.campaign_name})'
    
    class Meta:
        verbose_name = 'SB广告关键词数据'
        verbose_name_plural = 'SB广告关键词数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['create_date'])
        ]
        unique_together = ('market_id', 'create_date', 'campaign_id', 'group_id', 'keyword_id','match_type')  # 确保数据唯一性


# 在文件末尾添加以下代码
class AdsSbCampaign(BaseModel):
    """SB广告活动数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    targeting_type = models.CharField(max_length=100, verbose_name='目标类型', blank=True, null=True)
    ads_type = models.CharField(max_length=20, verbose_name='广告类型', default='sb')
    budget_type = models.CharField(max_length=100, verbose_name='预算类型', blank=True, null=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='预算', blank=True, null=True)
    state = models.CharField(max_length=20, verbose_name='状态', blank=True, null=True)
    serving_status = models.CharField(max_length=20, verbose_name='服务状态', blank=True, null=True)
    start_date = models.DateField(verbose_name='开始日期', blank=True, null=True)
    end_date = models.DateField(verbose_name='结束日期', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告商品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告商品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他商品销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    new_buyer_orders = models.IntegerField(verbose_name='新买家订单量', blank=True, null=True)
    new_buyer_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='新买家销售额', blank=True, null=True)
    page_views = models.IntegerField(verbose_name='页面浏览量', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)

    
    def __str__(self):
        return f'{self.campaign_name} ({self.campaign_id})'
    
    class Meta:
        verbose_name = 'SB广告活动数据'
        verbose_name_plural = 'SB广告活动数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_id']),
            models.Index(fields=['campaign_id']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'create_date', 'campaign_id')  # 确保数据唯一性


# SB广告创意数据模型
class AdsSbCreative(BaseModel):
    """SB广告创意数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    ad_id = models.CharField(max_length=100, verbose_name='广告ID', blank=True, null=True)
    ad_name = models.CharField(max_length=255, verbose_name='广告名称', blank=True, null=True)
    ads_type = models.CharField(max_length=50, verbose_name='广告类型', default='sb')
    creative_type = models.CharField(max_length=100, verbose_name='广告创意类型', blank=True, null=True)
    asins = models.TextField(verbose_name='ASIN列表', blank=True, null=True)
    state = models.CharField(max_length=50, verbose_name='状态', blank=True, null=True)
    serving_status = models.CharField(max_length=100, verbose_name='服务状态', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告商品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告商品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他商品销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    new_buyer_orders = models.IntegerField(verbose_name='新买家订单量', blank=True, null=True)
    new_buyer_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='新买家销售额', blank=True, null=True)
    page_views = models.IntegerField(verbose_name='页面浏览量', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)

    
    def __str__(self):
        return f'{self.ad_name or self.market_id} ({self.portfolio_name})'
    
    class Meta:
        verbose_name = 'SB广告创意数据'
        verbose_name_plural = 'SB广告创意数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['ad_name']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['create_date']),

        ]
        unique_together = ('market_id', 'ad_id', 'campaign_id', 'create_date', 'group_id','creative_type','asins')  # 确保数据唯一性


# SB广告目标投放数据模型
class AdsSbTargeting(BaseModel):
    """SB广告目标投放数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    targeting_id = models.CharField(max_length=100, verbose_name='目标投放ID', blank=True, null=True)
    bid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='竞价', blank=True, null=True)
    ads_type = models.CharField(max_length=20, verbose_name='广告类型', default='sb')
    state = models.CharField(max_length=20, verbose_name='状态', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告商品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告商品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他商品销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    new_buyer_orders = models.IntegerField(verbose_name='新买家订单量', blank=True, null=True)
    new_buyer_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='新买家销售额', blank=True, null=True)
    page_views = models.IntegerField(verbose_name='页面浏览量', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)


    
    def __str__(self):
        return f'{self.market_id} ({self.portfolio_name})'
    
    class Meta:
        verbose_name = 'SB广告目标投放数据'
        verbose_name_plural = 'SB广告目标投放数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['targeting_id']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['create_date']),
            models.Index(fields=['portfolio_name']),
        ]
        unique_together = ('market_id', 'targeting_id', 'create_date','campaign_id','group_id')  # 确保数据唯一性


# SB广告展示位置数据模型
class AdsSbPlacement(BaseModel):
    """SB广告展示位置数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    placement = models.CharField(max_length=255, verbose_name='展示位置', blank=True, null=True)
    targeting_type = models.CharField(max_length=255, verbose_name='目标投放类型', blank=True, null=True)
    ads_type = models.CharField(max_length=20, verbose_name='广告类型', default='sb')
    budget_type = models.CharField(max_length=20, verbose_name='预算类型', default='daily')
    budget = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='预算', blank=True, null=True)
    asins = models.TextField(verbose_name='ASIN列表', blank=True, null=True)
    state = models.CharField(max_length=20, verbose_name='状态', blank=True, null=True)
    serving_status = models.CharField(max_length=20, verbose_name='投放状态', blank=True, null=True)
    start_date = models.DateField(verbose_name='开始日期', default=timezone.now,blank=True, null=True)
    end_date = models.DateField(verbose_name='结束日期', default=timezone.now,blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告商品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告商品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他商品销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    new_buyer_orders = models.IntegerField(verbose_name='新买家订单量', blank=True, null=True)
    new_buyer_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='新买家销售额', blank=True, null=True)
    page_views = models.IntegerField(verbose_name='页面浏览量', blank=True, null=True)

        
    def __str__(self):
        return f'{self.market_id} ({self.portfolio_name})'
    
    class Meta:
        verbose_name = 'SB广告展示位置数据'
        verbose_name_plural = 'SB广告展示位置数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'campaign_id', 'create_date','placement')  # 确保数据唯一性


# SB广告搜索词数据模型
class AdsSbSearchTerms(BaseModel):
    """SB广告搜索词数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    keyword_id = models.CharField(max_length=100, verbose_name='搜索词ID', blank=True, null=True)
    keyword_text = models.CharField(max_length=255, verbose_name='搜索词', blank=True, null=True)
    query = models.CharField(max_length=255, verbose_name='查询', blank=True, null=True)
    match_type = models.CharField(max_length=255, verbose_name='匹配类型', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)

    def __str__(self):
        return f'{self.market_id} {self.portfolio_name}'
    
    class Meta:
        verbose_name = 'SB广告搜索词数据'
        verbose_name_plural = 'SB广告搜索词数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'campaign_id', 'group_id','create_date','keyword_id','query','match_type')  # 确保数据唯一性


# SD广告活动数据模型
class AdsSdCampaign(BaseModel):
    """SD广告活动数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.BigIntegerField(verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    group_id = models.BigIntegerField(verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    tactic = models.CharField(max_length=100, verbose_name='广告策略类型', blank=True, null=True)
    budget_type = models.CharField(max_length=100, verbose_name='广告预算类型', blank=True, null=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告预算', blank=True, null=True)
    cost_type = models.CharField(max_length=100, verbose_name='广告成本类型', blank=True, null=True)
    state = models.CharField(max_length=100, verbose_name='广告活动状态', blank=True, null=True)
    serving_status = models.CharField(max_length=100, verbose_name='广告活动服务状态', blank=True, null=True)
    start_date = models.DateField(verbose_name='广告活动开始日期', default=timezone.now,blank=True, null=True)
    end_date = models.DateField(verbose_name='广告活动结束日期', default=timezone.now,blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告产品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告产品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他产品销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    new_buyer_orders = models.IntegerField(verbose_name='新买家订单量', blank=True, null=True)
    new_buyer_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='新买家销售额', blank=True, null=True)
    page_views = models.IntegerField(verbose_name='页面浏览量', blank=True, null=True)
    
    def __str__(self):
        return f'{self.market_id} {self.portfolio_name}'
    
    class Meta:
        verbose_name = 'SD广告活动数据'
        verbose_name_plural = 'SD广告活动数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['create_date']),
            models.Index(fields=['state']),
        ]
        unique_together = ('market_id', 'campaign_id', 'group_id','create_date')  # 确保数据唯一性


# SD广告产品数据模型
class AdsSdProduct(BaseModel):
    """SD广告产品数据模型"""
    market_id = models.IntegerField(verbose_name='市场ID',blank=True, null=True)
    portfolio_id = models.CharField(max_length=100, verbose_name='广告组合ID', blank=True, null=True)
    portfolio_name = models.CharField(max_length=255, verbose_name='广告组合名称', blank=True, null=True)
    campaign_id = models.CharField(max_length=100, verbose_name='广告活动ID', blank=True, null=True)
    campaign_name = models.CharField(max_length=255, verbose_name='广告活动名称', blank=True, null=True)
    create_date = models.DateField(verbose_name='创建日期', default=timezone.now,blank=True, null=True)
    group_id = models.CharField(max_length=100, verbose_name='广告组ID', blank=True, null=True)
    group_name = models.CharField(max_length=255, verbose_name='广告组名称', blank=True, null=True)
    ad_id = models.CharField(max_length=100, verbose_name='广告ID', blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name='MSKU', blank=True, null=True)
    asin = models.CharField(max_length=50, verbose_name='ASIN', blank=True, null=True)
    cost_type = models.CharField(max_length=100, verbose_name='广告成本类型', blank=True, null=True)
    state = models.CharField(max_length=100, verbose_name='广告产品状态', blank=True, null=True)
    serving_status = models.CharField(max_length=100, verbose_name='广告产品服务状态', blank=True, null=True)
    impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    clicks = models.IntegerField(verbose_name='点击量', blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本', blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name='广告订单量', blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告销售额', blank=True, null=True)
    ads_product_orders = models.IntegerField(verbose_name='广告产品订单量', blank=True, null=True)
    ads_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='广告产品销售额', blank=True, null=True)
    other_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='其他产品销售额', blank=True, null=True)
    view_impressions = models.IntegerField(verbose_name='展示量', blank=True, null=True)
    new_buyer_orders = models.IntegerField(verbose_name='新买家订单量', blank=True, null=True)
    new_buyer_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='新买家销售额', blank=True, null=True)
    page_views = models.IntegerField(verbose_name='页面浏览量', blank=True, null=True)
    
    def __str__(self):
        return f'({self.market_id}) - {self.portfolio_name}'
    
    class Meta:
        verbose_name = 'SD广告产品数据'
        verbose_name_plural = 'SD广告产品数据列表'
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['portfolio_name']),
            models.Index(fields=['campaign_name']),
            models.Index(fields=['group_name']),
            models.Index(fields=['state']),
            models.Index(fields=['create_date']),
        ]
        unique_together = ('market_id', 'campaign_id', 'group_id','create_date','ad_id','msku','asin')


# 库存分类账数据模型
class InventoryStorageLedger(BaseModel):
    """库存分类账模型"""
    warehouse_name = models.CharField(max_length=100, verbose_name="仓库名称",blank=True, null=True)
    warehouse_id = models.CharField(max_length=100, verbose_name="仓库ID",blank=True, null=True)
    report_date = models.DateField(verbose_name="报告日期",blank=True, null=True)
    sku_name = models.CharField(max_length=255, verbose_name="SKU名称",blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name="SKU",blank=True, null=True)
    fnsku = models.CharField(max_length=50, verbose_name="FNSKU",blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name="MSKU",blank=True, null=True)
    source_msku = models.CharField(max_length=100, verbose_name="源MSKU",blank=True, null=True)
    asin = models.CharField(max_length=50, verbose_name="ASIN",blank=True, null=True)
    disposition = models.CharField(max_length=50, verbose_name="库存属性",blank=True, null=True)
    starting_warehouse_balance = models.IntegerField(verbose_name="期初库存",blank=True, null=True)
    ending_warehouse_balance = models.IntegerField(verbose_name="期末库存",blank=True, null=True)
    warehouse_transfer_in_and_out = models.IntegerField(verbose_name="仓库调拨入和调出数量",blank=True, null=True)
    in_transit_between_warehouses = models.IntegerField(verbose_name="在途库存",blank=True, null=True)
    receipts = models.IntegerField(verbose_name="接收数量",blank=True, null=True)
    customer_shipments = models.IntegerField(verbose_name="客户发货数量",blank=True, null=True)
    customer_returns = models.IntegerField(verbose_name="客户退货数量",blank=True, null=True)
    vendor_returns = models.IntegerField(verbose_name="供应商退货数量",blank=True, null=True)
    found = models.IntegerField(verbose_name="发现损坏数量",blank=True, null=True)
    lost = models.IntegerField(verbose_name="丢失数量",blank=True, null=True)
    damaged = models.IntegerField(verbose_name="损坏数量",blank=True, null=True)
    disposed = models.IntegerField(verbose_name="处置数量",blank=True, null=True)
    other_events = models.IntegerField(verbose_name="其他事件",blank=True, null=True)
    unknown_events = models.IntegerField(verbose_name="未知事件",blank=True, null=True)
    country = models.CharField(max_length=10, verbose_name="国家代码",blank=True, null=True)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    

    def __str__(self):
        return f"{self.report_date} - {self.warehouse_name}"
    
    class Meta:
        verbose_name = "库存分类账"
        verbose_name_plural = "库存分类账"
        unique_together = ('source_msku', 'warehouse_name', 'report_date', 'disposition', 'fnsku', 'country')


# 库存分类账明细数据模型
class InventoryStorageLedgerDetail(BaseModel):
    """库存分类账明细模型"""
    warehouse_name = models.CharField(max_length=100, verbose_name="仓库名称",blank=True, null=True)
    warehouse_id = models.CharField(max_length=100, verbose_name="仓库ID",blank=True, null=True)
    report_date = models.DateField(verbose_name="报告日期",blank=True, null=True)
    sku_name = models.CharField(max_length=255, verbose_name="SKU名称",blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name="SKU",blank=True, null=True)
    fnsku = models.CharField(max_length=50, verbose_name="FNSKU",blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name="MSKU",blank=True, null=True)
    source_msku = models.CharField(max_length=100, verbose_name="源MSKU",blank=True, null=True)
    asin = models.CharField(max_length=50, verbose_name="ASIN",blank=True, null=True)
    disposition = models.CharField(max_length=50, verbose_name="库存属性",blank=True, null=True)
    reference_id = models.CharField(max_length=100, verbose_name="参考ID",blank=True, null=True)
    quantity = models.IntegerField(verbose_name="数量",blank=True, null=True)
    event_type = models.CharField(max_length=50, verbose_name="事件类型",blank=True, null=True)
    fulfillment_center = models.CharField(max_length=100, verbose_name="fulfillmentCenter",blank=True, null=True)
    country = models.CharField(max_length=10, verbose_name="国家代码",blank=True, null=True)
    reason = models.CharField(max_length=255, verbose_name="原因",blank=True, null=True)
    reconciled_quantity = models.IntegerField(verbose_name="已调整数量",blank=True, null=True)
    unreconciled_quantity = models.IntegerField(verbose_name="未调整数量",blank=True, null=True)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    
    def __str__(self):
        return f"{self.sku} - {self.event_type} - {self.quantity} - {self.report_date}"
    
    class Meta:
        verbose_name = "库存分类账明细"
        verbose_name_plural = "库存分类账明细"
        # 可以根据实际需求设置适当的唯一约束
        # 这里假设每个SKU在特定日期和事件类型下可能有多个明细记录
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['report_date']),
            models.Index(fields=['event_type']),
            models.Index(fields=['warehouse_name']),
        ]
        unique_together = ('source_msku', 'warehouse_name', 'report_date', 'disposition', 'fnsku', 'country', 'event_type', 'fulfillment_center','reference_id')


# 交易数据模型
class Transaction(BaseModel):
    """交易数据模型"""
    market_id = models.IntegerField(verbose_name="市场ID",blank=True, null=True)
    market_name = models.CharField(max_length=100, verbose_name="市场名称",blank=True, null=True)
    currency = models.CharField(max_length=10, verbose_name="币种",blank=True, null=True)
    currency_symbol = models.CharField(max_length=10, verbose_name="币种符号",blank=True, null=True)
    create_date = models.DateTimeField(verbose_name="报表时间", auto_now_add=True)
    standard_date = models.DateTimeField(verbose_name="标准时间",blank=True, null=True)
    market_date = models.DateTimeField(verbose_name="市场时间",blank=True, null=True)
    zero_date = models.DateTimeField(verbose_name="零时区时间",blank=True, null=True)
    settlement_id = models.CharField(max_length=100, verbose_name="结算ID",blank=True, null=True)
    order_type = models.CharField(max_length=50, verbose_name="报表类型",blank=True, null=True)
    type = models.CharField(max_length=50, verbose_name="交易类型",blank=True, null=True)
    order_id = models.CharField(max_length=100, verbose_name="订单ID",blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name="SKU",blank=True, null=True)
    origin_sku = models.CharField(max_length=100, verbose_name="原始SKU",blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    quantity = models.IntegerField(verbose_name="数量",blank=True, null=True)
    market_place = models.CharField(max_length=100, verbose_name="市场",blank=True, null=True)
    fulfillment = models.CharField(max_length=100, verbose_name="配送类型",blank=True, null=True)
    order_city = models.CharField(max_length=100, verbose_name="订单城市",blank=True, null=True)
    order_state = models.CharField(max_length=100, verbose_name="订单状态",blank=True, null=True)
    order_postal = models.CharField(max_length=100, verbose_name="订单邮政编码",blank=True, null=True)
    tax_collection_model = models.CharField(max_length=100, verbose_name="征税模式",blank=True, null=True)
    product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="产品销售额",blank=True, null=True)
    product_sales_tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="产品销售税金",blank=True, null=True)
    shipping_credits = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="运费",blank=True, null=True)
    shipping_credits_tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="运费税金",blank=True, null=True)
    gift_wrap_credits = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="礼品包装费",blank=True, null=True)
    gift_wrap_credits_tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="礼品包装费税金",blank=True, null=True)
    regulatory_fees = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="监管费",blank=True, null=True)
    regulatory_fees_tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="监管费税金",blank=True, null=True)
    promotional_rebates = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="折扣金额",blank=True, null=True)
    promotional_rebates_tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="折扣金额税金",blank=True, null=True)
    points_granted = models.IntegerField(verbose_name="奖励积分",blank=True, null=True)
    marketplace_withheld_tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="市场预扣税",blank=True, null=True)
    selling_fees = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="销售佣金",blank=True, null=True)
    fba_fees = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="FBA费用",blank=True, null=True)
    other_transaction_fees = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="其他交易费用",blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="总计",blank=True, null=True)
    update_date = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    country_code = models.CharField(max_length=10, verbose_name="国家代码",blank=True, null=True)

    def __str__(self):
        return f"{self.type} - {self.total} - {self.standard_date}"
    
    class Meta:
        verbose_name = "交易记录"
        verbose_name_plural = "交易记录列表"
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['origin_sku']),
            models.Index(fields=['description']),
            models.Index(fields=['market_id']),
            models.Index(fields=['standard_date']),
            models.Index(fields=['sku']),
        ]
        


# 流量分析数据模型
class TrafficAnalysis(BaseModel):
    """流量分析数据模型"""
    market_id = models.CharField(max_length=100, verbose_name="市场ID",blank=True, null=True)
    market_name = models.CharField(max_length=100, verbose_name="市场名称",blank=True, null=True)
    parent_asin = models.CharField(max_length=100, verbose_name="父ASIN",blank=True, null=True)
    asin = models.CharField(max_length=100, verbose_name="ASIN",blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name="MSKU",blank=True, null=True)
    sessions = models.IntegerField(verbose_name="会话数",blank=True, null=True)
    browser_sessions = models.IntegerField(verbose_name="浏览器会话数",blank=True, null=True)
    app_sessions = models.IntegerField(verbose_name="应用会话数",blank=True, null=True)
    page_views = models.IntegerField(verbose_name="页面浏览数",blank=True, null=True)
    browser_page_views = models.IntegerField(verbose_name="浏览器页面浏览数",blank=True, null=True)
    app_page_views = models.IntegerField(verbose_name="应用页面浏览数",blank=True, null=True)
    buy_box_per = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="购买框占比",blank=True, null=True)
    units_ordered = models.IntegerField(verbose_name="订单数量",blank=True, null=True)
    units_ordered_b2b = models.IntegerField(verbose_name="B2B订单数量",blank=True, null=True)
    ordered_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="订单产品销售额",blank=True, null=True)
    ordered_product_sales_b2b = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="B2B订单产品销售额",blank=True, null=True)
    total_order_items = models.IntegerField(verbose_name="订单商品数量",blank=True, null=True)
    total_order_items_b2b = models.IntegerField(verbose_name="B2B订单商品数量",blank=True, null=True)
    record_date = models.DateField(verbose_name="记录日期",blank=True, null=True)
    

    class Meta:
        verbose_name = "流量分析"
        verbose_name_plural = "流量分析列表"
        indexes = [
            models.Index(fields=['asin']),
            models.Index(fields=['parent_asin']),
            models.Index(fields=['market_name']),
            models.Index(fields=['record_date']),
        ]
        unique_together = (('asin','msku', 'parent_asin', 'market_id', 'market_name', 'record_date'),)
    
    def __str__(self):
        return f"{self.record_date} - {self.market_name}"
        

# FBA库存数据模型
class FBAInventory(BaseModel):
    """FBA库存数据模型"""
    create_time = models.DateTimeField(verbose_name="添加时间", null=True, blank=True)
    warehouse_id = models.IntegerField(verbose_name="仓库ID",blank=True, null=True)
    warehouse_name = models.CharField(max_length=100, verbose_name="仓库名称",blank=True, null=True)
    warehouse_country = models.CharField(max_length=100, verbose_name="仓库国家",blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name="MSKU",blank=True, null=True)
    fnsku = models.CharField(max_length=100, verbose_name="FNSKU",blank=True, null=True)
    asin = models.CharField(max_length=100, verbose_name="ASIN",blank=True, null=True)
    single_quantity = models.IntegerField(verbose_name="装箱量",blank=True, null=True)
    product_delivery_days = models.IntegerField(verbose_name="采购交期",blank=True, null=True)
    purchase_plan_quantity = models.IntegerField(verbose_name="采购计划数量",blank=True, null=True)
    preassembly_plan_quantity = models.IntegerField(verbose_name="装配计划量",blank=True, null=True)
    plan_quantity = models.IntegerField(verbose_name="计划量",blank=True, null=True)
    order_quantity = models.IntegerField(verbose_name="采购量",blank=True, null=True)
    lot_no_quantity = models.IntegerField(verbose_name="交货量",blank=True, null=True)
    pl_poLn_qty = models.IntegerField(verbose_name="计采合交量",blank=True, null=True)
    transfer_pending_inventory_qty = models.IntegerField(verbose_name="调拨待出库（计划入库）",blank=True, null=True)
    transfer_pending_shipment_qty = models.IntegerField(verbose_name="调拨待出运（待出运量）",blank=True, null=True)
    erp_shipped_qty = models.IntegerField(verbose_name="已发货量",blank=True, null=True)
    erp_pending_inventory_qty = models.IntegerField(verbose_name="待入库量",blank=True, null=True)
    in_transit_qty = models.IntegerField(verbose_name="在途量",blank=True, null=True)
    working_quantity = models.IntegerField(verbose_name="货件处理中",blank=True, null=True)
    shipped_quantity = models.IntegerField(verbose_name="货件已发货",blank=True, null=True)
    receiving_quantity = models.IntegerField(verbose_name="货件正在接收",blank=True, null=True)
    inbound_total = models.IntegerField(verbose_name="入库总数量",blank=True, null=True)
    available_quantity = models.IntegerField(verbose_name="可售数量",blank=True, null=True)
    remote_available_quantity = models.IntegerField(verbose_name="远程可售",blank=True, null=True)
    local_available_quantity = models.IntegerField(verbose_name="本地可售",blank=True, null=True)
    fbm_available_quantity = models.IntegerField(verbose_name="FBM可售数量",blank=True, null=True)
    unsellable_quantity = models.IntegerField(verbose_name="不可售数量",blank=True, null=True)
    researching_quantity = models.IntegerField(verbose_name="调查中数量",blank=True, null=True)
    total_quantity = models.IntegerField(verbose_name="总数量",blank=True, null=True)
    reserved_future_supply = models.IntegerField(verbose_name="预留未来供应",blank=True, null=True)
    future_supply_buyable_quantity = models.IntegerField(verbose_name="未来供应可买数量",blank=True, null=True)
    historical_days_supply = models.IntegerField(verbose_name="历史天数供应",blank=True, null=True)
    fba_min_quantity = models.IntegerField(verbose_name="最低库存水平",blank=True, null=True)
    fba_inventory_health_status = models.CharField(max_length=100, verbose_name="FBA库存水平健康状态",blank=True, null=True)
    reserved_quantity = models.IntegerField(verbose_name="预留数量",blank=True, null=True)
    reserved_customer_orders = models.IntegerField(verbose_name="客户订单保留数量",blank=True, null=True)
    reserved_fc_processing = models.IntegerField(verbose_name="预留-处理中库存",blank=True, null=True)
    reserved_fc_transfer = models.IntegerField(verbose_name="预留-转运数量",blank=True, null=True)
    good_qty = models.IntegerField(verbose_name="良品数量",blank=True, null=True)
    defective_qty = models.IntegerField(verbose_name="次品数量",blank=True, null=True)
    unprocessed_reservation_qty = models.IntegerField(verbose_name="未处理预占",blank=True, null=True)
    processed_reservation_qty = models.IntegerField(verbose_name="已处理预占",blank=True, null=True)
    reservation_qty = models.IntegerField(verbose_name="预占数量",blank=True, null=True)
    available_qty = models.IntegerField(verbose_name="可用数量",blank=True, null=True)
    on_hand_qty = models.IntegerField(verbose_name="在手数量",blank=True, null=True)
    total_inventory_qty = models.IntegerField(verbose_name="总库存数量",blank=True, null=True)
    inventory_age_0_to_30_days = models.IntegerField(verbose_name="0-30天库存",blank=True, null=True)
    inventory_age_31_to_60_days = models.IntegerField(verbose_name="31-60天库存",blank=True, null=True)
    inventory_age_61_to_90_days = models.IntegerField(verbose_name="61-90天库存",blank=True, null=True)
    inventory_age_91_to_180_days = models.IntegerField(verbose_name="91-180天库存",blank=True, null=True)
    inventory_age_181_to_270_days = models.IntegerField(verbose_name="181-270天库存",blank=True, null=True)
    inventory_age_271_to_330_days = models.IntegerField(verbose_name="271-330天库存",blank=True, null=True)
    inventory_age_331_to_365_days = models.IntegerField(verbose_name="331-365天库存",blank=True, null=True)
    inventory_age_365_plus_days = models.IntegerField(verbose_name="365天以上库存",blank=True, null=True)
    obsolete_qty = models.IntegerField(verbose_name="obsoleteQty",blank=True, null=True)
    avg_units_ordered_7_days = models.IntegerField(verbose_name="avgUnitsOrdered7Days",blank=True, null=True)
    avg_units_ordered_15_days = models.IntegerField(verbose_name="avgUnitsOrdered15Days",blank=True, null=True)
    avg_units_ordered_30_days = models.IntegerField(verbose_name="avgUnitsOrdered30Days",blank=True, null=True)
    available_turnover_days = models.IntegerField(verbose_name="availableTurnoverDays",blank=True, null=True)
    inventory_turnover_days = models.IntegerField(verbose_name="inventoryTurnoverDays",blank=True, null=True)
    in_transit_turnover_days = models.IntegerField(verbose_name="inTransitTurnoverDays",blank=True, null=True)
    total_turnover_days = models.IntegerField(verbose_name="totalTurnoverDays",blank=True, null=True)
    shipment_in_transit_turnover_days = models.IntegerField(verbose_name="shipmentInTransitTurnoverDays",blank=True, null=True)
    shipment_total_turnover_days = models.IntegerField(verbose_name="shipmentTotalTurnoverDays",blank=True, null=True)
    update_time = models.DateTimeField(verbose_name="更新时间", auto_now=True, null=True)

    class Meta:
        verbose_name = "FBA库存"
        verbose_name_plural = "FBA库存列表"
        indexes = [
            models.Index(fields=['msku']),
            models.Index(fields=['asin']),
            models.Index(fields=['fnsku']),
            models.Index(fields=['warehouse_name']),
            models.Index(fields=['create_time']),
        ]
        unique_together = (('msku', 'fnsku', 'asin', 'warehouse_name', 'update_time','create_time', 'warehouse_country'),)
    
    def __str__(self):
        return f"{self.warehouse_name} - {self.update_time}"


# 月度仓储费数据模型
class MonStorageFee(BaseModel):
    """月度仓储费数据模型"""
    market_ids = models.JSONField(verbose_name="市场ID",blank=True, null=True)
    market_id = models.CharField(max_length=100, verbose_name="市场ID",blank=True, null=True)
    country_code = models.CharField(max_length=100, verbose_name="国家代码",blank=True, null=True)
    seller_sku = models.CharField(max_length=100, verbose_name="卖家SKU",blank=True, null=True)
    fnsku = models.CharField(max_length=100, verbose_name="FNSKU",blank=True, null=True)
    asin = models.CharField(max_length=100, verbose_name="ASIN",blank=True, null=True)
    fulfillment_center = models.CharField(max_length=100, verbose_name="仓储中心",blank=True, null=True)
    longest_side = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="最长边",blank=True, null=True)
    median_side = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="中值边",blank=True, null=True)
    shortest_side = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="最短边",blank=True, null=True)
    measurement_units = models.CharField(max_length=100, verbose_name="测量单位",blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="重量",blank=True, null=True)
    weight_units = models.CharField(max_length=100, verbose_name="重量单位",blank=True, null=True)
    item_volume = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="商品体积",blank=True, null=True)
    volume_units = models.CharField(max_length=100, verbose_name="体积单位",blank=True, null=True)
    product_size_tier = models.CharField(max_length=100, verbose_name="商品尺寸等级",blank=True, null=True)
    average_quantity_on_hand = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="平均库存数量",blank=True, null=True)
    average_quantity_pending_removal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="平均待移除数量",blank=True, null=True)
    estimated_total_item_volume = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="估计总商品体积",blank=True, null=True)
    month_of_charge = models.CharField(max_length=100, verbose_name="收费月份",blank=True, null=True)
    storage_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="仓储费率",blank=True, null=True)
    currency = models.CharField(max_length=100, verbose_name="货币",blank=True, null=True)
    estimated_monthly_storage_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="估计月度仓储费",blank=True, null=True)
    category = models.CharField(max_length=100, verbose_name="商品类型",blank=True, null=True)
    year = models.CharField(max_length=100, verbose_name="年份",blank=True, null=True)
    month = models.CharField(max_length=100, verbose_name="月份",blank=True, null=True)
    storage_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="仓储费",blank=True, null=True)


    class Meta:
        verbose_name = "月度仓储费"
        verbose_name_plural = "月度仓储费列表" # verbose_name_plural 是 verbose_name 的复数形式
        indexes = [
            models.Index(fields=['market_id']),
            models.Index(fields=['country_code']),
            models.Index(fields=['seller_sku']),
            models.Index(fields=['fnsku']),
            models.Index(fields=['asin']),
            models.Index(fields=['year']),
            models.Index(fields=['month']),
        ]
        unique_together = (('market_id', 'country_code', 'seller_sku', 'fnsku', 'asin', 'year', 'month', 'fulfillment_center'),)
    
    def __str__(self):
        return f"{self.year}-{self.month}-{self.market_id}"


# 利润分析数据模型
class ProfitAnalysis(BaseModel):
    """利润分析数据模型"""
    market_id = models.IntegerField(verbose_name="市场ID",blank=True, null=True)
    warehouse_id = models.IntegerField(verbose_name="仓储中心ID",blank=True, null=True)
    market_name = models.CharField(max_length=100, verbose_name="市场名称",blank=True, null=True)
    country_id = models.IntegerField(verbose_name="国家ID",blank=True, null=True)
    country_name = models.CharField(max_length=100, verbose_name="国家名称",blank=True, null=True)
    currency = models.CharField(max_length=100, verbose_name="货币",blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name="MSKU",blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name="SKU",blank=True, null=True)
    asin = models.CharField(max_length=100, verbose_name="ASIN",blank=True, null=True)
    statistics_date = models.DateField(verbose_name="统计日期",blank=True, null=True)
    order_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="订单商品销售额",blank=True, null=True)
    discount_cost_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="实际销售额",blank=True, null=True)
    bogus_sales_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="推广订单销售额",blank=True, null=True)
    bogus_discount_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="推广折扣成本",blank=True, null=True)
    discount_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="折扣成本",blank=True, null=True)
    order_product_sales_b2b = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="订单商品销售额（B2B）",blank=True, null=True)
    orders = models.IntegerField(verbose_name="订单数",blank=True, null=True)
    order_items = models.IntegerField(verbose_name="订单商品种类量",blank=True, null=True)
    order_items_b2b = models.IntegerField(verbose_name="订单商品数（B2B）",blank=True, null=True)
    units_ordered = models.IntegerField(verbose_name="订单商品数（B2B）",blank=True, null=True)
    units_ordered_b2b = models.IntegerField(verbose_name="订单商品数（B2B）",blank=True, null=True)
    units_ordered_traffic = models.IntegerField(verbose_name="流量",blank=True, null=True)
    order_bogus_count = models.IntegerField(verbose_name="推广销量",blank=True, null=True)
    bogus_orders = models.IntegerField(verbose_name="推广订单量",blank=True, null=True)
    avg_order_items = models.IntegerField(verbose_name="平均订单商品种类数",blank=True, null=True)
    avg_order_items_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="平均订单价格",blank=True, null=True)
    avg_units_ordered_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="平均订单商品销售额",blank=True, null=True)
    natural_orders = models.IntegerField(verbose_name="自然订单量",blank=True, null=True)
    patch_units_ordered = models.IntegerField(verbose_name="补单量",blank=True, null=True)
    multi_channel_orders = models.IntegerField(verbose_name="多渠道订单数",blank=True, null=True)
    refunds = models.IntegerField(verbose_name="退款订单数",blank=True, null=True)
    returns = models.IntegerField(verbose_name="退货订单数",blank=True, null=True)
    returns_sellable = models.IntegerField(verbose_name="可售退货订单数",blank=True, null=True)
    returns_purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="退货补回采购成本",blank=True, null=True)
    returns_arrive_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="退货补回到库成本",blank=True, null=True)
    refund_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="亚马逊退款",blank=True, null=True)
    return_product_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="退款销售额",blank=True, null=True)
    refund_discount_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="退款折扣成本",blank=True, null=True)
    refund_tax_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="退款补税金成本",blank=True, null=True)
    order_ids = models.TextField(verbose_name="订单ID列表",blank=True, null=True)
    ads_impressions = models.IntegerField(verbose_name="广告展示量",blank=True, null=True)
    ads_clicks = models.IntegerField(verbose_name="广告点击量",blank=True, null=True)
    ads_orders = models.IntegerField(verbose_name="广告订单数",blank=True, null=True)
    ads_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="广告销售额",blank=True, null=True)
    ads_spend = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="广告花费",blank=True, null=True)
    ads_item_orders = models.IntegerField(verbose_name="广告商品订单数",blank=True, null=True)
    ads_natural_orders = models.IntegerField(verbose_name="广告自然订单数",blank=True, null=True)
    ads_item_sales = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="广告商品销售额",blank=True, null=True)
    commission_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="佣金成本",blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="配送成本",blank=True, null=True)
    fba_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="FBA配送成本",blank=True, null=True)
    fbm_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="FBM配送成本",blank=True, null=True)
    amazon_tax_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="亚马逊税金成本",blank=True, null=True)
    others_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="其他成本",blank=True, null=True)
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="采购成本",blank=True, null=True)
    arrive_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="到库成本",blank=True, null=True)
    product_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="买家运费",blank=True, null=True)
    vat_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="VAT税",blank=True, null=True)
    sales_gross_profit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="销售额毛利",blank=True, null=True)
    sales_net_profit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="销售额净利润",blank=True, null=True)
    patch_amazon_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="补单成本",blank=True, null=True)
    patch_purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="补单采购成本",blank=True, null=True)
    patch_arrive_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="补单到库成本",blank=True, null=True)
    multichannel_amazon_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="多渠道亚马逊成本",blank=True, null=True)
    multichannel_purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="多渠道采购成本",blank=True, null=True)
    multichannel_arrive_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="多渠道到库成本",blank=True, null=True)
    storage_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="存储费用",blank=True, null=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="销售价格",blank=True, null=True)
    fba_quantity = models.IntegerField(verbose_name="FBA可售",blank=True, null=True)
    fba_turnover = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="FBA可售周转",blank=True, null=True)
    fbm_quantity = models.IntegerField(verbose_name="FBM可售",blank=True, null=True)
    fbm_turnover = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="FBM可售周转",blank=True, null=True)
    main_seller_rank = models.IntegerField(verbose_name="大类排名",blank=True, null=True)
    seller_rank = models.IntegerField(verbose_name="小类排名",blank=True, null=True)
    seller_rank_category = models.CharField(max_length=255, verbose_name="小类排名分类",blank=True, null=True)
    main_seller_rank_category = models.CharField(max_length=255, verbose_name="大类排名分类",blank=True, null=True)
    star = models.DecimalField(max_digits=3, decimal_places=2, verbose_name="星级",blank=True, null=True)
    review_quantity = models.IntegerField(verbose_name="评论数",blank=True, null=True)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="平台费用",blank=True, null=True)
    fulfillment = models.CharField(max_length=255, verbose_name="fulfillment",blank=True, null=True)
    reserved_transfers = models.IntegerField(verbose_name="调拨中（FBA）",blank=True, null=True)
    reserved_trocessing = models.IntegerField(verbose_name="处理中（FBA）",blank=True, null=True)
    plan_storage_quantity = models.IntegerField(verbose_name="计划入库（FBA）",blank=True, null=True)
    shipped_quantity = models.IntegerField(verbose_name="已发货（FBA）",blank=True, null=True)
    receiving_quantity = models.IntegerField(verbose_name="入库中（FBA）",blank=True, null=True)
    deal = models.CharField(max_length=255, verbose_name="Deal花费",blank=True, null=True)
    coupon = models.CharField(max_length=255, verbose_name="Coupon花费",blank=True, null=True)
    

    class Meta:
        verbose_name = "销售数据"
        verbose_name_plural = verbose_name
        unique_together = ('market_id', 'statistics_date', 'msku','asin')


# 促销-秒杀
class promotion_deal(BaseModel):
    """
    /operation/ads/deal/query
    促销模型-秒杀
    """
    market_id = models.CharField(max_length=100, verbose_name="市场ID",blank=True, null=True)


# 销售排名数据模型
class SalesRank(BaseModel):
    """销售排名数据模型"""
    market_id = models.CharField(max_length=100, verbose_name="市场ID",blank=True, null=True)
    market_name = models.CharField(max_length=100, verbose_name="市场名称",blank=True, null=True)
    statistics_date = models.DateField(verbose_name="统计日期",blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name="MSKU",blank=True, null=True)
    asin = models.CharField(max_length=100, verbose_name="ASIN",blank=True, null=True)
    main_seller_rank = models.IntegerField(verbose_name="大类排名",blank=True, null=True)
    seller_rank = models.IntegerField(verbose_name="小类排名",blank=True, null=True)
    seller_rank_category = models.CharField(max_length=255, verbose_name="小类排名分类",blank=True, null=True)
    main_seller_rank_category = models.CharField(max_length=255, verbose_name="大类排名分类",blank=True, null=True)
    star = models.DecimalField(max_digits=3, decimal_places=2, verbose_name="星级",blank=True, null=True)
    review_quantity = models.IntegerField(verbose_name="评论数",blank=True, null=True)
    

# 销售预估数据模型
class SalesForecast(BaseModel):
    """销售预估数据模型"""
    market_id = models.CharField(max_length=100, verbose_name="市场ID",blank=True, null=True)
    market_name = models.CharField(max_length=100, verbose_name="市场名称",blank=True, null=True)
    asin = models.CharField(max_length=100, verbose_name="ASIN",blank=True, null=True)
    parent_asin = models.CharField(max_length=100, verbose_name="父ASIN",blank=True, null=True)
    msku = models.CharField(max_length=100, verbose_name="MSKU",blank=True, null=True)
    
    # 当前库存数据
    current_available_quantity = models.IntegerField(verbose_name="当前可售库存",blank=True, null=True)
    current_reserved_quantity = models.IntegerField(verbose_name="当前预留库存",blank=True, null=True)
    
    # 周转数据
    turnover_days = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="预计周转天数",blank=True, null=True)
    daily_sales_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="日销售率",blank=True, null=True)
    
    # 预估参数
    forecast_method = models.CharField(max_length=50, verbose_name="预估方法",blank=True, null=True)  # 如: 'moving_average', 'linear_regression', 'seasonal'
    forecast_start_date = models.DateField(verbose_name="预估开始日期",blank=True, null=True)
    forecast_end_date = models.DateField(verbose_name="预估结束日期",blank=True, null=True)
    
    # 基础预估数据
    forecasted_units = models.IntegerField(verbose_name="预估销售数量",blank=True, null=True)
    forecasted_sales = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="预估销售额",blank=True, null=True)
    
    # 月份预估（未来12个月）
    month_1_forecast = models.IntegerField(verbose_name="第1个月预估销量",blank=True, null=True)
    month_2_forecast = models.IntegerField(verbose_name="第2个月预估销量",blank=True, null=True)
    month_3_forecast = models.IntegerField(verbose_name="第3个月预估销量",blank=True, null=True)
    month_4_forecast = models.IntegerField(verbose_name="第4个月预估销量",blank=True, null=True)
    month_5_forecast = models.IntegerField(verbose_name="第5个月预估销量",blank=True, null=True)
    month_6_forecast = models.IntegerField(verbose_name="第6个月预估销量",blank=True, null=True)
    month_7_forecast = models.IntegerField(verbose_name="第7个月预估销量",blank=True, null=True)
    month_8_forecast = models.IntegerField(verbose_name="第8个月预估销量",blank=True, null=True)
    month_9_forecast = models.IntegerField(verbose_name="第9个月预估销量",blank=True, null=True)
    month_10_forecast = models.IntegerField(verbose_name="第10个月预估销量",blank=True, null=True)
    month_11_forecast = models.IntegerField(verbose_name="第11个月预估销量",blank=True, null=True)
    month_12_forecast = models.IntegerField(verbose_name="第12个月预估销量",blank=True, null=True)
    
    # 生成时间
    generated_at = models.DateTimeField(verbose_name="预估生成时间", auto_now=True)
    
    class Meta:
        verbose_name = "销售预估"
        verbose_name_plural = "销售预估列表"
        indexes = [
            models.Index(fields=['asin']),
            models.Index(fields=['parent_asin']),
            models.Index(fields=['market_name']),
            models.Index(fields=['forecast_method']),
            models.Index(fields=['generated_at']),
        ]
    
    def __str__(self):
        return f"{self.market_name} - {self.asin} - {self.forecast_method}"



# 汇率模型
class CurrencyRate(BaseModel):
    """汇率模型"""
    currency = models.CharField(max_length=3, verbose_name="货币代码",blank=True, null=True)
    currency_symbol = models.CharField(max_length=10, verbose_name="货币符号",blank=True, null=True)
    currency_name = models.CharField(max_length=255, verbose_name="货币名称",blank=True, null=True)
    reference_rate = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="官方汇率",blank=True, null=True)
    custom_rate = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="自定义汇率",blank=True, null=True)
    state = models.CharField(max_length=20, verbose_name="状态",blank=True, null=True)
    month_date = models.CharField(max_length=7, verbose_name="月份",blank=True, null=True)
    last_date = models.DateTimeField(verbose_name="最后更新日期",blank=True, null=True)

    class Meta:
        verbose_name = "汇率"
        verbose_name_plural = "汇率列表"
        indexes = [
            models.Index(fields=['currency']),
            models.Index(fields=['month_date']),
        ]
        unique_together = ('currency', 'month_date')
