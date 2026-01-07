from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import AmazonProfile, AmazonCampaign, AmazonAdGroup, AmazonKeyword, AmazonReport
from .services.api_service1 import AmazonAdvertisingAPIService
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 首页视图
def dashboard(request):
    """仪表盘首页"""
    profiles = AmazonProfile.objects.all()
    campaigns = AmazonCampaign.objects.all()[:10]  # 显示最近10个活动
    
    context = {
        'profiles': profiles,
        'campaigns': campaigns,
    }
    return render(request, 'api/dashboard.html', context)

# 配置文件视图
def profiles_view(request):
    """配置文件列表视图"""
    if request.method == 'POST':
        # 从API获取配置文件数据
        try:
            api_service = AmazonAdvertisingAPIService()
            profiles_data = api_service.get_profiles()
            
            # 保存到数据库
            for profile in profiles_data.get('profiles', []):
                AmazonProfile.objects.update_or_create(
                    profile_id=profile.get('profileId'),
                    defaults={
                        'profile_name': profile.get('profileName', 'Unknown'),
                        'country_code': profile.get('countryCode'),
                        'marketplace_string_id': profile.get('marketplaceStringId'),
                        'is_default': profile.get('isDefault', False),
                    }
                )
            return JsonResponse({'status': 'success', 'message': '配置文件更新成功'})
        except Exception as e:
            logger.error(f"获取配置文件失败: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    profiles = AmazonProfile.objects.all()
    return render(request, 'api/profiles.html', {'profiles': profiles})

# 活动视图
def campaigns_view(request):
    """活动列表视图"""
    profiles = AmazonProfile.objects.all()
    campaigns = AmazonCampaign.objects.all()
    
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        if profile_id:
            try:
                api_service = AmazonAdvertisingAPIService()
                campaigns_data = api_service.get_campaigns(profile_id)
                
                # 保存到数据库
                profile = AmazonProfile.objects.get(profile_id=profile_id)
                for campaign in campaigns_data.get('campaigns', []):
                    AmazonCampaign.objects.update_or_create(
                        campaign_id=campaign.get('campaignId'),
                        defaults={
                            'profile': profile,
                            'campaign_name': campaign.get('name', 'Unknown'),
                            'campaign_type': campaign.get('campaignType', ''),
                            'state': campaign.get('state', ''),
                            'budget': campaign.get('dailyBudget', 0),
                            'budget_type': campaign.get('budgetType', ''),
                            'start_date': datetime.strptime(campaign.get('startDate', ''), '%Y%m%d').date() if campaign.get('startDate') else None,
                            'end_date': datetime.strptime(campaign.get('endDate', ''), '%Y%m%d').date() if campaign.get('endDate') else None,
                        }
                    )
                return JsonResponse({'status': 'success', 'message': '活动数据更新成功'})
            except Exception as e:
                logger.error(f"获取活动数据失败: {str(e)}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return render(request, 'api/campaigns.html', {'profiles': profiles, 'campaigns': campaigns})

# 广告组视图
def ad_groups_view(request):
    """广告组列表视图"""
    campaigns = AmazonCampaign.objects.all()
    ad_groups = AmazonAdGroup.objects.all()
    
    if request.method == 'POST':
        campaign_id = request.POST.get('campaign_id')
        if campaign_id:
            try:
                campaign = AmazonCampaign.objects.get(campaign_id=campaign_id)
                api_service = AmazonAdvertisingAPIService()
                ad_groups_data = api_service.get_ad_groups(campaign.profile.profile_id)
                
                # 保存到数据库
                for ad_group in ad_groups_data.get('adGroups', []):
                    # 只保存与当前活动相关的广告组
                    if ad_group.get('campaignId') == int(campaign_id):
                        AmazonAdGroup.objects.update_or_create(
                            ad_group_id=ad_group.get('adGroupId'),
                            defaults={
                                'campaign': campaign,
                                'ad_group_name': ad_group.get('name', 'Unknown'),
                                'state': ad_group.get('state', ''),
                                'default_bid': ad_group.get('defaultBid', 0),
                            }
                        )
                return JsonResponse({'status': 'success', 'message': '广告组数据更新成功'})
            except Exception as e:
                logger.error(f"获取广告组数据失败: {str(e)}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return render(request, 'api/ad_groups.html', {'campaigns': campaigns, 'ad_groups': ad_groups})

# 关键词视图
def keywords_view(request):
    """关键词列表视图"""
    ad_groups = AmazonAdGroup.objects.all()
    keywords = AmazonKeyword.objects.all()
    
    if request.method == 'POST':
        ad_group_id = request.POST.get('ad_group_id')
        if ad_group_id:
            try:
                ad_group = AmazonAdGroup.objects.get(ad_group_id=ad_group_id)
                api_service = AmazonAdvertisingAPIService()
                keywords_data = api_service.get_keywords(ad_group.campaign.profile.profile_id)
                
                # 保存到数据库
                for keyword in keywords_data.get('keywords', []):
                    # 只保存与当前广告组相关的关键词
                    if keyword.get('adGroupId') == int(ad_group_id):
                        AmazonKeyword.objects.update_or_create(
                            keyword_id=keyword.get('keywordId'),
                            defaults={
                                'ad_group': ad_group,
                                'keyword_text': keyword.get('keywordText', ''),
                                'match_type': keyword.get('matchType', ''),
                                'state': keyword.get('state', ''),
                                'bid': keyword.get('bid', 0),
                            }
                        )
                return JsonResponse({'status': 'success', 'message': '关键词数据更新成功'})
            except Exception as e:
                logger.error(f"获取关键词数据失败: {str(e)}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return render(request, 'api/keywords.html', {'ad_groups': ad_groups, 'keywords': keywords})

# 报表视图
def reports_view(request):
    """报表视图"""
    profiles = AmazonProfile.objects.all()
    reports = AmazonReport.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        report_type = request.POST.get('report_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if profile_id and report_type and start_date and end_date:
            try:
                profile = AmazonProfile.objects.get(profile_id=profile_id)
                api_service = AmazonAdvertisingAPIService()
                
                # 创建报表配置
                report_config = {
                    'name': f'{report_type}_{start_date}_{end_date}',
                    'startDate': start_date.replace('-', ''),
                    'endDate': end_date.replace('-', ''),
                    'configuration': {
                        'adProduct': 'SPONSORED_PRODUCTS',
                        'columns': ['campaignName', 'campaignId', 'impressions', 'clicks', 'cost', 'attributedConversions14d', 'attributedSales14d']
                    }
                }
                
                # 创建报表
                report_data = api_service.create_report(profile_id, report_config)
                
                # 保存报表信息
                AmazonReport.objects.create(
                    profile=profile,
                    report_id=report_data.get('reportId'),
                    report_type=report_type,
                    status=report_data.get('status', 'IN_PROGRESS'),
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
                    end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
                )
                
                return JsonResponse({'status': 'success', 'message': '报表创建成功，正在生成中'})
            except Exception as e:
                logger.error(f"创建报表失败: {str(e)}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return render(request, 'api/reports.html', {'profiles': profiles, 'reports': reports})

# API数据更新视图
@csrf_exempt
def update_api_data(request):
    """更新API数据的通用视图"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            endpoint = data.get('endpoint')
            
            api_service = AmazonAdvertisingAPIService()
            
            if endpoint == 'profiles':
                profiles_data = api_service.get_profiles()
                return JsonResponse({'status': 'success', 'data': profiles_data})
            elif endpoint == 'campaigns':
                profile_id = data.get('profile_id')
                if profile_id:
                    campaigns_data = api_service.get_campaigns(profile_id)
                    return JsonResponse({'status': 'success', 'data': campaigns_data})
                return JsonResponse({'status': 'error', 'message': '缺少profile_id参数'}, status=400)
            elif endpoint == 'ad_groups':
                profile_id = data.get('profile_id')
                if profile_id:
                    ad_groups_data = api_service.get_ad_groups(profile_id)
                    return JsonResponse({'status': 'success', 'data': ad_groups_data})
                return JsonResponse({'status': 'error', 'message': '缺少profile_id参数'}, status=400)
            elif endpoint == 'keywords':
                profile_id = data.get('profile_id')
                if profile_id:
                    keywords_data = api_service.get_keywords(profile_id)
                    return JsonResponse({'status': 'success', 'data': keywords_data})
                return JsonResponse({'status': 'error', 'message': '缺少profile_id参数'}, status=400)
            else:
                return JsonResponse({'status': 'error', 'message': '未知的端点'}, status=404)
        except Exception as e:
            logger.error(f"更新API数据失败: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': '只支持POST请求'}, status=405)
