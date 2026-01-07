from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from .tasks.views import ScheduledTaskViewSet



@permission_classes([AllowAny])
def product_list_view(request):
    """产品列表页面"""
    return render(request, 'product/product_list.html')


@permission_classes([AllowAny])
def inventory_list_view(request):
    """库存列表页面"""
    return render(request, 'inventory/inventory_list.html')


@permission_classes([AllowAny])
def sync_dashboard_view(request):
    """数据同步仪表盘页面"""
    return render(request, 'sync/sync_dashboard.html')


@permission_classes([AllowAny])
def status_check_view(request):
    """系统状态检查页面"""
    return render(request, 'status/status_check.html')


class HomeView(TemplateView):
    """首页视图"""
    template_name = 'home.html'
    permission_classes = [AllowAny]


@permission_classes([AllowAny])
def sales_forecast_view(request):
    """
    销售预估页面
    request: HttpRequest对象，包含请求信息
    """
    return render(request, 'sales/sales_forecast.html')


@permission_classes([AllowAny])
def task_manager_view(request):
    """
    定时任务管理页面
    request: HttpRequest对象，包含请求信息
    """
    # 定义可用的任务函数列表
    task_options = [
        {
            'value': 'api.views.sync_products_from_gerpgo',
            'label': '同步产品数据'
        },
        {
            'value': 'api.views.sync_fba_inventory_from_gerpgo',
            'label': '同步FBA库存数据'
        },
        {
            'value': 'api.views.sync_marketplaces_from_gerpgo',
            'label': '同步店铺市场数据'
        },
        {
            'value': 'api.views.sync_sp_ad_data_from_gerpgo',
            'label': '同步SP广告产品数据'
        },
        {
            'value': 'api.views.sync_sp_kw_data_from_gerpgo',
            'label': '同步SP广告关键词数据'
        },
        {
            'value': 'api.views.sync_sp_target_data_from_gerpgo',
            'label': '同步SP广告投放数据'
        },
        {
            'value': 'api.views.sync_sp_placement_data_from_gerpgo',
            'label': '同步SP广告展示位置数据'
        },
        {
            'value': 'api.views.sync_sp_search_terms_data_from_gerpgo',
            'label': '同步SP广告搜索词数据'
        },
        {
            'value': 'api.views.sync_sb_kw_data_from_gerpgo',
            'label': '同步SB广告关键词数据'
        },
        {
            'value': 'api.views.sync_sb_campaign_data_from_gerpgo',
            'label': '同步SB广告活动数据'
        },
        {
            'value': 'api.views.sync_sb_creative_data_from_gerpgo',
            'label': '同步SB广告创意数据'
        },
        {
            'value': 'api.views.sync_sb_targeting_data_from_gerpgo',
            'label': '同步SB广告投放数据'
        },
        {
            'value': 'api.views.sync_sb_placement_data_from_gerpgo',
            'label': '同步SB广告展示位置数据'
        },
        {
            'value': 'api.views.sync_sb_search_terms_data_from_gerpgo',
            'label': '同步SB广告搜索词数据'
        },
        {
            'value': 'api.views.sync_sd_campaign_data_from_gerpgo',
            'label': '同步SD广告活动数据'
        },
        {
            'value': 'api.views.sync_sd_product_data_from_gerpgo',
            'label': '同步SD广告产品数据'
        },
        {
            'value': 'api.views.sync_inventory_storage_ledger_from_gerpgo',
            'label': '同步库存分类账数据'
        },
        {
            'value': 'api.views.sync_inventory_storage_ledger_detail',
            'label': '同步库存分类账详情数据'
        },
        {
            'value': 'api.views.sync_transaction',
            'label': '同步交易数据'
        },
        {
            'value': 'api.views.sync_traffic_analysis',
            'label': '同步流量分析数据'
        },
        {
            'value': 'api.views.sync_fba_inventory_full_from_gerpgo',
            'label': '同步restock数据'
        },
        {
            'value': 'api.views.sync_mon_storage_fee',
            'label': '同步库存仓储费'
        },
        {
            'value': 'api.views.sync_profit_analysis',
            'label': '同步利润分析数据'
        },
        {
            'value': 'api.views.sync_currency_rates',
            'label': '同步汇率数据'
        },
    ]
    
    # 将task_options传递给模板
    return render(request, 'tasks/task_manager.html', {'task_options': task_options})
