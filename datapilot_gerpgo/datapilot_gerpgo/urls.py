"""
URL configuration for datapilot_gerpgo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from api.views_frontend import (
    product_list_view,
    inventory_list_view,
    sync_dashboard_view,
    status_check_view,
    HomeView,
    task_manager_view,
    sales_forecast_view
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('', HomeView.as_view(), name='home'),
    path('products/', product_list_view, name='product_list'),
    path('inventory/', inventory_list_view, name='inventory_list'),
    path('sync/', sync_dashboard_view, name='sync_dashboard'),
    path('status/', status_check_view, name='status_check'),
    path('tasks/', task_manager_view, name='task_manager'),
    path('sales/forecast/', sales_forecast_view, name='sales_forecast'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
