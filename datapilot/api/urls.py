from django.urls import path
from . import views

urlpatterns = [
    # 页面视图
    path('', views.dashboard, name='dashboard'),
    path('profiles/', views.profiles_view, name='profiles'),
    path('campaigns/', views.campaigns_view, name='campaigns'),
    path('ad_groups/', views.ad_groups_view, name='ad_groups'),
    path('keywords/', views.keywords_view, name='keywords'),
    path('reports/', views.reports_view, name='reports'),
    
    # API视图
    path('api/update/', views.update_api_data, name='update_api_data'),
]