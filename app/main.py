from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import db
from app.routers import api
from app.scheduler import fetch_scheduler
from app.scrapers.base import close_playwright_browser

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.init()
    fetch_scheduler.start()
    yield
    # Shutdown
    fetch_scheduler.shutdown()
    await close_playwright_browser()


app = FastAPI(
    title="海外短剧爆款监控",
    description="定时抓取海外各大短剧平台的爆款短剧数据",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(api.router)

# 前端页面（纯静态文件，无需Jinja2模板引擎）
@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "scheduler": fetch_scheduler.get_status()}
