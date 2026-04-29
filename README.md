# 海外短剧爆款监控

定时抓取 DramaBox、ReelShort、ShortMax、FlexTV、Sereal+ 等海外短剧平台的爆款榜单数据。

## 功能特性

- **多平台监控**：覆盖6大头部海外短剧平台
- **双榜单**：近期热剧榜、新剧飙升榜
- **三维度**：今日、本周、本月
- **定时更新**：每3分钟自动抓取
- **可视化前端**：Web页面实时查看
- **CSV导出**：支持按条件导出数据
- **反爬机制**：代理IP轮换、User-Agent轮换、随机延迟、失败重试

## 技术栈

- Python 3.10+ + FastAPI
- SQLite（轻量单文件数据库）
- httpx（异步HTTP）+ Playwright（SPA渲染备用）
- APScheduler（定时任务）
- Tailwind CSS（前端样式）

## 安装步骤

### 1. 克隆/下载项目

```bash
cd drama_monitor
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt

# 安装 Playwright 浏览器（备用渲染需要）
playwright install chromium
```

### 4. 配置代理IP（重要）

编辑 `app/config.py`，在 `PROXY_POOL` 中填入您的代理IP：

```python
PROXY_POOL = [
    "http://your-proxy-ip:port",
    "http://user:pass@host:port",
]
```

> 由于目标平台有严格的反爬机制（Cloudflare等），**必须配置代理IP**才能正常抓取。

### 5. 启动应用

```bash
# Windows
start.bat

# macOS/Linux
./start.sh
```

或直接使用 uvicorn：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. 访问系统

- **前端页面**：http://localhost:8000/
- **API文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/health

## 项目结构

```
drama_monitor/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 全局配置（代理、平台URL）
│   ├── database.py          # SQLite 异步操作
│   ├── models.py            # 数据模型
│   ├── scheduler.py         # APScheduler 定时任务
│   ├── routers/
│   │   ├── api.py           # REST API
│   │   └── views.py         # 前端页面路由
│   ├── scrapers/
│   │   ├── base.py          # 爬虫基类（反爬、重试）
│   │   ├── dramabox.py
│   │   ├── reelshort.py
│   │   ├── shortmax.py
│   │   ├── flextv.py
│   │   └── serealplus.py
│   ├── services/
│   │   └── export_service.py # CSV导出
│   └── templates/
│       └── index.html        # 监控前端页面
├── data/
│   └── drama_monitor.db     # SQLite数据库
├── requirements.txt
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rankings` | 查询榜单数据（支持过滤、分页）|
| GET | `/api/platforms` | 获取平台列表 |
| GET | `/api/stats` | 获取数据统计 |
| GET | `/api/export/csv` | 导出CSV文件 |
| POST | `/api/trigger` | 手动触发抓取 |
| GET | `/api/scheduler/status` | 获取调度器状态 |

## 平台接口调研说明

由于目标平台以APP为主且反爬严格，各平台的实际API端点需要在代理环境下通过抓包或页面分析确定。

每个平台的爬虫文件（`app/scrapers/*.py`）中已预留：
- `API_ENDPOINTS`：API端点配置（需根据实际抓包填写）
- `_fetch_api()`：JSON API抓取逻辑
- `_fetch_html()`：HTML解析逻辑（备用）
- `fetch_with_playwright()`：Playwright渲染（基类提供）

### 调研建议

1. **抓包分析**：使用 Charles、Fiddler 或浏览器开发者工具抓取APP或网页端的榜单API
2. **更新配置**：将实际API地址填入 `API_ENDPOINTS`
3. **调整字段映射**：根据实际响应结构调整字段提取逻辑
4. **测试验证**：通过 `/api/trigger` 手动触发测试

## 反爬配置

在 `app/config.py` 中可调整：

- `PROXY_POOL`：代理IP池
- `USER_AGENT_POOL`：User-Agent池
- `REQUEST_DELAY_MIN/MAX`：请求间隔（默认1-3秒）
- `MAX_RETRIES`：失败重试次数（默认3次）
- `RETRY_BACKOFF`：退避基数
- `FETCH_INTERVAL_MINUTES`：抓取间隔（默认3分钟）

## 部署到云服务器

1. 将代码上传至服务器
2. 安装依赖（同上）
3. 使用 systemd 或 supervisor 管理 uvicorn 进程
4. 建议使用 Nginx 反向代理

示例 systemd 服务文件：

```ini
[Unit]
Description=Drama Monitor
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/drama_monitor
Environment="PATH=/path/to/drama_monitor/venv/bin"
ExecStart=/path/to/drama_monitor/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 注意事项

1. **法律合规**：请确保抓取行为符合目标平台的服务条款及当地法律法规
2. **代理IP**：目标平台反爬严格，无代理情况下几乎无法访问
3. **频率控制**：请勿将抓取间隔设置过短，避免对目标平台造成压力
4. **数据准确性**：平台榜单数据随时可能变化，本系统仅供参考
