"""
API URL配置
"""
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from . import views
from .tasks.views import ScheduledTaskViewSet, TaskExecutionLogViewSet

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'sync/logs', views.SyncLogViewSet, basename='sync-log')
router.register(r'products', views.ProductViewSet, basename='product')
# 注册定时任务相关视图集
router.register(r'tasks', ScheduledTaskViewSet, basename='scheduled-task')
router.register(r'task-logs', TaskExecutionLogViewSet, basename='task-execution-log')

# 在前端数据接口部分添加
# 在现有urlpatterns中添加以下内容
urlpatterns = [
    # 添加重定向，解决sync-logs 404错误
    re_path(r'^sync-logs/(?P<path>.*)$', RedirectView.as_view(url='/api/v1/sync/logs/%(path)s', permanent=True)),
    

    # 数据同步接口
    path('sync/products/', views.sync_products_from_gerpgo, name='sync-products'),
    # 添加库存同步接口
    path('sync/inventory/', views.sync_fba_inventory_from_gerpgo, name='sync-inventory'),
    # 添加店铺同步接口
    path('sync/marketplaces/', views.sync_marketplaces_from_gerpgo, name='sync-marketplaces'),
    # 添加SP广告数据同步接口
    path('sync/sp_ad_data/', views.sync_sp_ad_data_from_gerpgo, name='sync-sp-ad-data'),
    # 添加SP关键词数据同步接口
    path('sync/sp_kw_data/', views.sync_sp_kw_data_from_gerpgo, name='sync-sp-kw-data'),
    # 添加SPTarget数据同步接口
    path('sync/sp_target_data/', views.sync_sp_target_data_from_gerpgo, name='sync-sp-target-data'),
    path('sync/sp_placement_data/', views.sync_sp_placement_data_from_gerpgo, name='sync-sp-placement-data'),
    # 添加SP搜索词数据同步接口
    path('sync/sp_search_terms_data/', views.sync_sp_search_terms_data_from_gerpgo, name='sync-sp-search-terms-data'),
    # 添加SB广告关键词数据同步接口
    path('sync/sb_kw_data/', views.sync_sb_kw_data_from_gerpgo, name='sync-sb-kw-data'),
    # 添加SB广告活动数据同步接口
    path('sync/sb_creative_data/', views.sync_sb_creative_data_from_gerpgo, name='sync-sb-creative-data'),
    # 添加SB广告活动数据同步接口
    path('sync/sb_campaign_data/', views.sync_sb_campaign_data_from_gerpgo, name='sync-sb-campaign-data'),
    # 添加SBTargeting数据同步接口
    path('sync/sb_targeting_data/', views.sync_sb_targeting_data_from_gerpgo, name='sync-sb-targeting-data'),
    # 添加SBPlacement数据同步接口
    path('sync/sb_placement_data/', views.sync_sb_placement_data_from_gerpgo, name='sync-sb-placement-data'),
    # 添加SB搜索词数据同步接口
    path('sync/sb_search_terms_data/', views.sync_sb_search_terms_data_from_gerpgo, name='sync-sb-search-terms-data'),
    # 添加SD广告活动数据同步接口
    path('sync/sd_campaign_data/', views.sync_sd_campaign_data_from_gerpgo, name='sync-sd-campaign-data'),
    # 添加SD产品数据同步接口
    path('sync/sd_product_data/', views.sync_sd_product_data_from_gerpgo, name='sync-sd-product-data'),
    # 添加库存前端数据接口
    path('sync/inventory_storage_ledger/', views.sync_inventory_storage_ledger_from_gerpgo, name='sync-inventory-storage-ledger'),
    # 添加库存分类账明细数据同步接口
    path('sync/inventory_storage_ledger_detail/', views.sync_inventory_storage_ledger_detail, name='sync-inventory-storage-ledger-detail'),
    # 添加交易数据同步接口
    path('sync/transaction/', views.sync_transaction, name='sync-transaction'),
    # 添加流量分析数据同步接口
    path('sync/traffic_analysis/', views.sync_traffic_analysis, name='sync-traffic-analysis'),
    # 添加FBA库存数据同步接口
    path('sync/fba_inventory_full/', views.sync_fba_inventory_full_from_gerpgo, name='sync-fba-inventory-full'),
    # 添加存储费用数据同步接口  
    path('sync/mon_storage_fee/', views.sync_mon_storage_fee, name='sync-mon-storage-fee'),
    # 添加利润分析数据同步接口
    path('sync/profit_analysis/', views.sync_profit_analysis, name='sync-profit-analysis'),
    
    # 销售预估接口
    path('sales/generate-forecasts/', views.generate_forecasts, name='generate-sales-forecasts'),
    path('sales/get-forecasts/', views.get_sales_forecasts, name='get-sales-forecasts'),


    # 前端数据接口
    path('get-sp-ad-data/', views.get_sp_ad_data, name='get-sp-ad-data'),
    path('get-sp-kw-data/', views.get_sp_kw_data, name='get-sp-kw-data'),
    path('get-sp-target-data/', views.get_sp_target_data, name='get-sp-target-data'),
    path('get-sp-placement-data/', views.get_sp_placement_data, name='get-sp-placement-data'),
    path('get-sp-search-terms-data/', views.get_sp_search_terms_data, name='get-sp-search-terms-data'),
    # 添加SB广告关键词前端数据接口
    path('get-sb-kw-data/', views.get_sb_kw_data, name='get-sb-kw-data'),
    # 添加SB广告活动前端数据接口
    path('get-sb-campaign-data/', views.get_sb_campaign_data, name='get-sb-campaign-data'),
    
    # 包含路由器生成的URLs
    path('', include(router.urls)),
]