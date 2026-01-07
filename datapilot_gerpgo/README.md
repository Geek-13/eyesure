# Datapilot

一个基于 Django 的应用，用于集成 Amazon Advertising API，展示与管理广告配置文件（Profiles）、广告活动（Campaigns）、广告组（AdGroups）、关键词（Keywords）以及报表（Reports）。项目包含基础页面、数据更新接口以及认证、请求和数据处理等工具模块。

## 功能概览
- 仪表盘首页展示配置文件与近期活动
- Profiles、Campaigns、AdGroups、Keywords 列表与数据拉取
- Reports 创建与状态记录
- 亚马逊广告 API 集成与令牌刷新
- 开发环境 CORS/DRF 配置与文件/控制台日志

## 技术栈
- Python 3.x, Django 5.x
- Django REST Framework
- requests
- django-cors-headers
- python-dotenv
- 注意：utils/data_processing.py 中使用了 pandas 与 numpy（见下文依赖提示）

## 目录结构（关键部分）
- datapilot/ — 项目配置（settings、urls、wsgi）
- api/ — 业务应用（models、views、urls、services、migrations、templates）
- utils/ — 工具模块（auth_utils、request_utils、data_processing）
- templates/ — 页面模板（api/dashboard、profiles、campaigns 等）
- static/ — 静态资源（css/js）
- .env — 环境变量（不应提交到版本库）
- requirements.txt — 依赖列表

## 快速开始

1) 创建并激活虚拟环境，安装依赖
- python -m venv .venv
- .venv\Scripts\activate  （Windows）
- pip install -r requirements.txt

2) 配置环境变量（项目根目录 .env）
基本：
- SECRET_KEY=your_django_secret_key
- DEBUG=True
- ALLOWED_HOSTS=127.0.0.1,localhost

亚马逊广告：
- AMAZON_CLIENT_ID=your_client_id
- AMAZON_CLIENT_SECRET=your_client_secret
- AMAZON_REFRESH_TOKEN=your_refresh_token
- AMAZON_REGION=na  （或 eu / fe）
- AMAZON_API_VERSION=v3

3) 初始化数据库
- python manage.py migrate
- 可选：python manage.py createsuperuser

4) 启动服务
- python manage.py runserver

## 页面与接口
页面（datapilot/api/urls.py）：
- / — Dashboard
- /profiles/ — Profiles
- /campaigns/ — Campaigns
- /ad_groups/ — Ad Groups
- /keywords/ — Keywords
- /reports/ — Reports

数据更新接口：
- POST /api/update/
- 请求体示例：
  - {"endpoint":"profiles"}
  - {"endpoint":"campaigns","profile_id":123456789}
  - {"endpoint":"ad_groups","profile_id":123456789}
  - {"endpoint":"keywords","profile_id":123456789}

示例（curl）：
- curl -X POST http://127.0.0.1:8000/api/update/ -H "Content-Type: application/json" -d "{\"endpoint\":\"profiles\"}"

## 日志
- 默认写入 datapilot.log 并输出到控制台（开发环境 DEBUG 级别）。生产环境建议降低日志级别并采用滚动日志。

## 依赖与注意事项
- utils/data_processing.py 使用了 pandas 与 numpy。若需运行该模块相关功能，请在 requirements.txt 中补充：
  - pandas>=2.0.0
  - numpy>=1.26.0
- 接口默认在开发环境较为开放；生产环境需开启鉴权（如 DRF Token 或 Session）并限制访问。

## 常见问题
- 令牌刷新：AmazonAdvertisingAPIService 初始化时会刷新访问令牌；请求前需确保令牌有效。
- CORS：开发环境可允许全部来源；生产环境请设置白名单。
- SECRET_KEY：生产环境必须通过 .env 提供，避免使用不安全的默认值。

## 生产部署建议
- 使用 PostgreSQL/MySQL 等生产数据库，通过环境变量配置（建议 DATABASE_URL 方案）
- 将 DEBUG=False 并正确设置 ALLOWED_HOSTS
- 严格的认证与权限控制（IsAuthenticated、Token/Session）
- 日志脱敏、滚动与归档
- 添加单元测试与 CI 流水线（测试、lint、安全检查）