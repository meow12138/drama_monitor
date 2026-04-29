from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from app.database import db
from app.models import RankingQuery, DramaItemOut, StatsItem, PlatformInfo
from app.services.export_service import ExportService
from app.scheduler import fetch_scheduler
from app.config import PLATFORMS

router = APIRouter(prefix="/api")
export_service = ExportService(db)


@router.get("/rankings", response_model=dict)
async def get_rankings(
    platform: Optional[str] = Query(None, description="平台Key，如 dramabox"),
    rank_type: Optional[str] = Query("hot", description="hot 或 rising"),
    time_period: Optional[str] = Query("today", description="today/week/month"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """查询榜单数据"""
    items, total = await db.get_rankings(
        platform=platform,
        rank_type=rank_type,
        time_period=time_period,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/platforms", response_model=list)
async def get_platforms():
    """获取支持的平台列表"""
    return [
        PlatformInfo(
            key=key,
            name=info["name"],
            base_url=info["base_url"],
        )
        for key, info in PLATFORMS.items()
    ]


@router.get("/stats", response_model=list)
async def get_stats():
    """获取各平台数据统计"""
    return await db.get_stats()


@router.get("/export/csv")
async def export_csv(
    platform: Optional[str] = Query(None),
    rank_type: Optional[str] = Query(None),
    time_period: Optional[str] = Query(None),
):
    """导出CSV文件"""
    data = await export_service.export_csv(
        platform=platform,
        rank_type=rank_type,
        time_period=time_period,
    )
    filename = export_service.generate_filename(platform, rank_type, time_period)
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/trigger")
async def trigger_fetch():
    """手动触发一次全量抓取（调试用）"""
    try:
        count = await fetch_scheduler.fetch_all_platforms(source="manual")
        return {"status": "success", "fetched_items": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def get_compare(
    rank_type: str = Query("hot", description="hot 或 rising"),
    time_period: str = Query("today", description="today/week/month"),
    top_n: int = Query(20, ge=1, le=100, description="跨平台总榜取前 N 条"),
):
    """跨平台播放量横向对比"""
    cross_ranking = await db.get_cross_ranking(rank_type, time_period, top_n)
    platform_summary = await db.get_platform_summary(rank_type, time_period)
    return {
        "cross_ranking": cross_ranking,
        "platform_summary": platform_summary,
    }


@router.get("/scheduler/status")
async def scheduler_status():
    """获取定时调度器状态"""
    return fetch_scheduler.get_status()
