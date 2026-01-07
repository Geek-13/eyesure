from django.db import models
from django.utils import timezone

class AmazonProfile(models.Model):
    """亚马逊广告配置文件模型"""
    profile_id = models.IntegerField(unique=True, verbose_name="配置文件ID")
    profile_name = models.CharField(max_length=255, verbose_name="配置文件名称")
    country_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="国家代码")
    marketplace_string_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="市场ID")
    is_default = models.BooleanField(default=False, verbose_name="是否默认")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.profile_name} ({self.profile_id})"

    class Meta:
        verbose_name = "亚马逊广告配置文件"
        verbose_name_plural = "亚马逊广告配置文件"

class AmazonCampaign(models.Model):
    """亚马逊广告活动模型"""
    profile = models.ForeignKey(AmazonProfile, on_delete=models.CASCADE, related_name="campaigns", verbose_name="配置文件")
    campaign_id = models.IntegerField(unique=True, verbose_name="活动ID")
    campaign_name = models.CharField(max_length=255, verbose_name="活动名称")
    campaign_type = models.CharField(max_length=50, verbose_name="活动类型")
    state = models.CharField(max_length=50, verbose_name="状态")
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="预算")
    budget_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="预算类型")
    start_date = models.DateField(blank=True, null=True, verbose_name="开始日期")
    end_date = models.DateField(blank=True, null=True, verbose_name="结束日期")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.campaign_name} ({self.campaign_id})"

    class Meta:
        verbose_name = "亚马逊广告活动"
        verbose_name_plural = "亚马逊广告活动"

class AmazonAdGroup(models.Model):
    """亚马逊广告组模型"""
    campaign = models.ForeignKey(AmazonCampaign, on_delete=models.CASCADE, related_name="ad_groups", verbose_name="广告活动")
    ad_group_id = models.IntegerField(unique=True, verbose_name="广告组ID")
    ad_group_name = models.CharField(max_length=255, verbose_name="广告组名称")
    state = models.CharField(max_length=50, verbose_name="状态")
    default_bid = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="默认出价")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.ad_group_name} ({self.ad_group_id})"

    class Meta:
        verbose_name = "亚马逊广告组"
        verbose_name_plural = "亚马逊广告组"

class AmazonKeyword(models.Model):
    """亚马逊关键词模型"""
    ad_group = models.ForeignKey(AmazonAdGroup, on_delete=models.CASCADE, related_name="keywords", verbose_name="广告组")
    keyword_id = models.IntegerField(unique=True, verbose_name="关键词ID")
    keyword_text = models.CharField(max_length=255, verbose_name="关键词文本")
    match_type = models.CharField(max_length=50, verbose_name="匹配类型")
    state = models.CharField(max_length=50, verbose_name="状态")
    bid = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name="出价")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.keyword_text} ({self.keyword_id})"

    class Meta:
        verbose_name = "亚马逊关键词"
        verbose_name_plural = "亚马逊关键词"

class AmazonReport(models.Model):
    """亚马逊广告报表模型"""
    profile = models.ForeignKey(AmazonProfile, on_delete=models.CASCADE, related_name="reports", verbose_name="配置文件")
    report_id = models.CharField(max_length=255, unique=True, verbose_name="报表ID")
    report_type = models.CharField(max_length=255, verbose_name="报表类型")
    status = models.CharField(max_length=50, default="IN_PROGRESS", verbose_name="状态")
    download_url = models.URLField(blank=True, null=True, verbose_name="下载链接")
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(verbose_name="结束日期")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.report_type} - {self.report_id}"

    class Meta:
        verbose_name = "亚马逊广告报表"
        verbose_name_plural = "亚马逊广告报表"
