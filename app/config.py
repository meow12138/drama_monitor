import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "drama_monitor.db"

# 代理IP池，支持环境变量 PROXY_POOL，格式: http://host:port,http://host2:port2
_env_proxies = os.getenv("PROXY_POOL", "").strip()
if _env_proxies:
    PROXY_POOL = [p.strip() for p in _env_proxies.split(",") if p.strip()]
else:
    PROXY_POOL = [
        # 在此填入您的代理IP
        # 示例: "http://127.0.0.1:8080",
    ]

# User-Agent 池
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# 请求配置（支持环境变量覆盖）
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "1.0"))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "3.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "2.0"))

# 平台配置
PLATFORMS = {
    "dramabox": {
        "name": "DramaBox",
        "base_url": "https://www.dramabox.com",
    },
    "reelshort": {
        "name": "ReelShort",
        "base_url": "https://www.reelshort.com",
    },
    "shortmax": {
        "name": "ShortMax",
        "base_url": "https://www.shorttv.live",
    },
    "moboreader": {
        "name": "MoboReader",
        "base_url": "https://www.moboreader.com",
    },
    "flextv": {
        "name": "FlexTV",
        "base_url": "https://www.flextv.cc",
    },
    "serealplus": {
        "name": "Sereal+",
        "base_url": "https://www.sereal.plus",
    },
    "netshort": {
        "name": "NetShort",
        "base_url": "https://netshort.com",
    },
    "melolo": {
        "name": "Melolo",
        "base_url": "https://melolo.com",
    },
    "goodshort": {
        "name": "GoodShort",
        "base_url": "https://www.goodshort.com",
    },
    "moboreels": {
        "name": "MoboReels",
        "base_url": "https://www.moboreels.com",
    },
}

# 抓取配置（支持环境变量覆盖）
FETCH_LIMIT = int(os.getenv("FETCH_LIMIT", "50"))
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "3"))

# 时区
TIMEZONE = os.getenv("TIMEZONE", "UTC")
