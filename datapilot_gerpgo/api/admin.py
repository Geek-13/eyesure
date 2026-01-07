from django.contrib import admin
from .models import (
    SyncLog, Product, Market, SellerMarketplace, Inventory, 
    AdsSpProduct, AdsSpKeyword, AdsSpTarget, AdsSpPlacement, AdsSpSearchTerms,
    AdsSbKeyword, AdsSbCampaign, AdsSbCreative, AdsSbTargeting, AdsSbPlacement, AdsSbSearchTerms,
    AdsSdCampaign, AdsSdProduct, InventoryStorageLedger, InventoryStorageLedgerDetail,
    Transaction, TrafficAnalysis, FBAInventory, MonStorageFee, ProfitAnalysis,
    promotion_deal, SalesRank, SalesForecast, CurrencyRate
)

# Register your models here.

# 自定义SyncLog管理类
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('sync_type', 'start_time', 'end_time', 'status', 'total_count', 'success_count', 'failed_count')
    list_filter = ('sync_type', 'status', 'start_time')
    search_fields = ('sync_type', 'status')
    readonly_fields = ('start_time', 'end_time', 'total_count', 'success_count', 'failed_count')

# 自定义Product管理类
class ProductAdmin(admin.ModelAdmin):
    list_display = ('market_name', 'sku', 'product_name', 'category_name', 'status', 'created_at')
    list_filter = ('market_name', 'category_name', 'status', 'created_at')
    search_fields = ('sku', 'product_name', 'market_name')
    readonly_fields = ('created_at', 'updated_at')

# 自定义Market管理类
class MarketAdmin(admin.ModelAdmin):
    list_display = ('market_name', 'market', 'seller_id', 'state', 'created_at')
    list_filter = ('market', 'state', 'created_at')
    search_fields = ('market_name', 'market', 'seller_id')

# 自定义Inventory管理类
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'sku', 'market_place', 'available_quantity', 'warehouse_name', 'created_at')
    list_filter = ('market_place', 'warehouse_name', 'created_at')
    search_fields = ('product_name', 'sku', 'market_place')

# 自定义Transaction管理类
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('type', 'order_id', 'sku', 'product_sales', 'currency', 'standard_date')
    list_filter = ('type', 'currency', 'market_name', 'standard_date')
    search_fields = ('order_id', 'sku', 'market_name')

# 自定义TrafficAnalysis管理类
class TrafficAnalysisAdmin(admin.ModelAdmin):
    list_display = ('market_name', 'asin', 'msku', 'sessions', 'units_ordered', 'record_date')
    list_filter = ('market_name', 'record_date')
    search_fields = ('asin', 'msku', 'market_name')

# 自定义FBAInventory管理类
class FBAInventoryAdmin(admin.ModelAdmin):
    list_display = ('warehouse_name', 'msku', 'asin', 'available_quantity', 'total_quantity', 'update_time')
    list_filter = ('warehouse_name', 'update_time')
    search_fields = ('msku', 'asin', 'warehouse_name')

# 自定义MonStorageFee管理类
class MonStorageFeeAdmin(admin.ModelAdmin):
    list_display = ('market_id', 'seller_sku', 'asin', 'month_of_charge', 'estimated_monthly_storage_fee')
    list_filter = ('market_id', 'month_of_charge')
    search_fields = ('seller_sku', 'asin', 'market_id')

# 自定义ProfitAnalysis管理类
class ProfitAnalysisAdmin(admin.ModelAdmin):
    list_display = ('market_name', 'msku', 'asin', 'order_product_sales', 'sales_net_profit', 'statistics_date')
    list_filter = ('market_name', 'statistics_date')
    search_fields = ('msku', 'asin', 'market_name')

# 自定义CurrencyRate管理类
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'currency_name', 'reference_rate', 'custom_rate', 'month_date')
    list_filter = ('currency', 'month_date')
    search_fields = ('currency', 'currency_name')

# 自定义广告SP产品数据管理类
class AdsSpProductAdmin(admin.ModelAdmin):
    list_display = ('market_id', 'campaign_name', 'msku', 'asin', 'impressions', 'clicks', 'cost', 'create_date')
    list_filter = ('market_id', 'campaign_name', 'create_date')
    search_fields = ('msku', 'asin', 'campaign_name')

# 自定义广告SP关键词数据管理类
class AdsSpKeywordAdmin(admin.ModelAdmin):
    list_display = ('market_id', 'campaign_name', 'keyword_text', 'match_type', 'impressions', 'clicks', 'cost', 'create_date')
    list_filter = ('market_id', 'campaign_name', 'match_type', 'create_date')
    search_fields = ('keyword_text', 'campaign_name')

# 自定义广告SB活动数据管理类
class AdsSbCampaignAdmin(admin.ModelAdmin):
    list_display = ('market_id', 'campaign_name', 'budget', 'state', 'impressions', 'clicks', 'cost', 'create_date')
    list_filter = ('market_id', 'state', 'create_date')
    search_fields = ('campaign_name', 'market_id')

# 自定义广告SD活动数据管理类
class AdsSdCampaignAdmin(admin.ModelAdmin):
    list_display = ('market_id', 'campaign_name', 'budget', 'state', 'impressions', 'clicks', 'cost', 'create_date')
    list_filter = ('market_id', 'state', 'create_date')
    search_fields = ('campaign_name', 'market_id')

# 注册模型和自定义管理类
admin.site.register(SyncLog, SyncLogAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Market, MarketAdmin)
admin.site.register(SellerMarketplace)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(AdsSpProduct, AdsSpProductAdmin)
admin.site.register(AdsSpKeyword, AdsSpKeywordAdmin)
admin.site.register(AdsSpTarget)
admin.site.register(AdsSpPlacement)
admin.site.register(AdsSpSearchTerms)
admin.site.register(AdsSbKeyword)
admin.site.register(AdsSbCampaign, AdsSbCampaignAdmin)
admin.site.register(AdsSbCreative)
admin.site.register(AdsSbTargeting)
admin.site.register(AdsSbPlacement)
admin.site.register(AdsSbSearchTerms)
admin.site.register(AdsSdCampaign, AdsSdCampaignAdmin)
admin.site.register(AdsSdProduct)
admin.site.register(InventoryStorageLedger)
admin.site.register(InventoryStorageLedgerDetail)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(TrafficAnalysis, TrafficAnalysisAdmin)
admin.site.register(FBAInventory, FBAInventoryAdmin)
admin.site.register(MonStorageFee, MonStorageFeeAdmin)
admin.site.register(ProfitAnalysis, ProfitAnalysisAdmin)
admin.site.register(promotion_deal)
admin.site.register(SalesRank)
admin.site.register(SalesForecast)
admin.site.register(CurrencyRate, CurrencyRateAdmin)