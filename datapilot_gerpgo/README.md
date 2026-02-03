# datapilot_gerpgo

一个基于 Django 和 Gerpgo API 的数据同步与管理系统，用于从 Gerpgo 平台同步各类业务数据到本地数据库，并提供定时任务管理、数据可视化等功能。

## 功能特性

- **数据同步**：从 Gerpgo API 同步产品、库存、广告、销售等数据
- **定时任务**：支持自定义 Cron 表达式的定时任务管理
- **相对时间选择**：支持按相对天数（如30天）设置同步时间范围
- **多维度数据**：支持同步产品、FBA库存、广告（SP/SB/SD）、流量分析、利润分析等数据
- **数据可视化**：提供产品列表、库存列表、数据同步仪表盘等可视化页面
- **系统状态检查**：提供API状态和系统健康检查功能
- **RESTful API**：提供完整的 RESTful API 接口
- **跨域支持**：内置 CORS 配置，支持前端跨域请求

## 技术栈

- Python 3.x
- Django 5.x
- Django REST Framework
- PostgreSQL
- APScheduler（定时任务）
- requests（HTTP请求）
- django-cors-headers（跨域支持）
- python-dotenv（环境变量管理）
- python-dateutil（日期时间处理）
- pytz（时区处理）

## 目录结构

```
datapilot_gerpgo/
├── api/                    # 业务应用
│   ├── migrations/         # 数据库迁移文件
│   ├── services/           # 服务层（API客户端等）
│   ├── tasks/              # 定时任务相关
│   ├── tests/              # 测试文件
│   ├── __init__.py
│   ├── admin.py            # Django 管理后台
│   ├── apps.py             # 应用配置
│   ├── models.py           # 数据模型
│   ├── serializers.py      # DRF 序列化器
│   ├── urls.py             # API 路由
│   ├── views.py            # API 视图
│   └── views_frontend.py   # 前端页面视图
├── datapilot_gerpgo/       # 项目配置
│   ├── __init__.py
│   ├── asgi.py             # ASGI 配置
│   ├── settings.py         # Django 设置
│   ├── urls.py             # 项目路由
│   └── wsgi.py             # WSGI 配置
├── templates/              # 页面模板
│   ├── base/               # 基础模板
│   ├── inventory/          # 库存相关模板
│   ├── product/            # 产品相关模板
│   ├── sales/              # 销售相关模板
│   ├── status/             # 状态检查模板
│   ├── sync/               # 同步仪表盘模板
│   ├── tasks/              # 任务管理模板
│   └── home.html           # 首页
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── auth_utils.py       # 认证工具
│   ├── data_processing.py  # 数据处理工具
│   └── request_utils.py    # 请求工具
├── .gitignore              # Git 忽略文件
├── README.md               # 项目文档
├── manage.py               # Django 管理脚本
└── requirements.txt        # 依赖列表
```

## 快速开始

### 1. 环境准备

1. **创建虚拟环境**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件，添加以下配置：

```env
# Django 配置
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Gerpgo API 配置
GERPGO_APP_ID=your_gerpgo_app_id
GERPGO_APP_KEY=your_gerpgo_app_key
GERPGO_API_BASE_URL=https://open.gerpgo.com/api/open/

# 数据库配置（可选，默认使用 settings.py 中的配置）
# DB_NAME=gerpgoApi
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432
```

### 3. 数据库配置

项目默认使用 PostgreSQL 数据库，配置如下：

- 数据库名：`gerpgoApi`
- 用户名：`postgres`
- 密码：`eyesure5211..`
- 主机：`localhost`
- 端口：`5432`

如果需要修改数据库配置，请编辑 `datapilot_gerpgo/settings.py` 文件中的 `DATABASES` 部分。

### 4. 初始化数据库

```bash
# 执行数据库迁移
python manage.py migrate

# 创建超级用户（可选，用于访问 Django 管理后台）
python manage.py createsuperuser
```

### 5. 启动服务

```bash
python manage.py runserver
```

服务启动后，可以通过以下地址访问：
- 首页：`http://127.0.0.1:8000/`
- 定时任务管理：`http://127.0.0.1:8000/tasks/`
- API 文档：`http://127.0.0.1:8000/api/`

## 使用指南

### 1. 定时任务管理

1. **访问定时任务管理页面**：`http://127.0.0.1:8000/tasks/`

2. **创建定时任务**：
   - 填写任务名称
   - 选择任务函数（如 `api.views.sync_products_from_gerpgo`）
   - 设置 Cron 表达式（如 `0 0 * * *` 表示每天凌晨执行）
   - 设置任务参数（可选），如 `{"relative_days": 30}` 表示同步最近30天的数据
   - 选择任务状态为 "ACTIVE"
   - 点击 "保存" 按钮

3. **管理任务**：
   - 可以暂停、恢复或删除任务
   - 可以查看任务执行日志

### 2. 数据同步

1. **手动同步**：
   - 访问数据同步仪表盘：`http://127.0.0.1:8000/sync/`
   - 选择需要同步的数据类型
   - 设置同步参数
   - 点击 "同步" 按钮

2. **定时同步**：
   - 通过定时任务管理页面创建定时任务
   - 设置合适的 Cron 表达式
   - 配置同步参数

### 3. 相对时间参数使用

在创建定时任务时，可以使用 `relative_days` 参数设置相对时间范围：

```json
{"relative_days": 30}
```

这表示同步最近30天的数据，系统会自动计算开始日期和结束日期。

## API 接口

### 核心同步接口

- **同步产品数据**：`POST /api/sync-products/`
- **同步 FBA 库存**：`POST /api/sync-fba-inventory/`
- **同步 SP 广告产品**：`POST /api/sync-sp-ad-data/`
- **同步 SP 广告关键词**：`POST /api/sync-sp-kw-data/`
- **同步流量分析**：`POST /api/sync-traffic-analysis/`
- **同步利润分析**：`POST /api/sync-profit-analysis/`
- **同步汇率数据**：`POST /api/sync-currency-rates/`

### 系统接口

- **API 状态检查**：`GET /api/status/`
- **定时任务管理**：`GET /api/tasks/`
- **任务执行日志**：`GET /api/task-execution-logs/`

## 常见问题

### 1. 定时任务不执行

- 检查任务状态是否为 "ACTIVE"
- 检查 Cron 表达式是否正确
- 检查任务函数路径是否正确
- 查看任务执行日志获取详细错误信息

### 2. 同步数据时间范围不正确

- 确保使用了正确的时间参数格式
- 使用 `relative_days` 参数时，确保值为整数
- 检查 `task_wrapper` 函数是否正确处理了时间参数

### 3. 数据库连接失败

- 确保 PostgreSQL 服务已启动
- 确保数据库名、用户名、密码配置正确
- 确保数据库用户有足够的权限

### 4. API 调用失败

- 检查 Gerpgo API 配置是否正确
- 确保网络连接正常
- 检查 Gerpgo 平台的 API 权限设置

## 生产部署建议

1. **环境配置**：
   - 设置 `DEBUG=False`
   - 配置 `ALLOWED_HOSTS` 为实际域名
   - 使用强密码作为 `SECRET_KEY`

2. **数据库配置**：
   - 使用生产级 PostgreSQL 配置
   - 启用数据库连接池
   - 定期备份数据库

3. **定时任务**：
   - 使用 Supervisor 或 Systemd 管理定时任务进程
   - 合理设置任务执行频率，避免 API 调用过于频繁

4. **日志管理**：
   - 配置详细的日志记录
   - 使用日志轮转工具管理日志文件
   - 考虑使用 ELK 等日志分析系统

5. **安全配置**：
   - 启用 HTTPS
   - 配置适当的 CORS 策略
   - 实现 API 访问认证

6. **监控与告警**：
   - 监控系统运行状态
   - 设置 API 调用失败告警
   - 监控定时任务执行情况

## 开发指南

### 代码规范

- 遵循 PEP 8 代码规范
- 使用中文注释说明复杂逻辑
- 保持代码结构清晰，模块化设计

### 测试

```bash
# 运行测试
python manage.py test

# 运行特定应用的测试
python manage.py test api
```

### 代码质量

```bash
# 安装代码质量工具
pip install flake8 black

# 检查代码质量
flake8 .

# 自动格式化代码
black .
```

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请联系项目维护者。