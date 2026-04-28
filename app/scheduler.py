import asyncio
import traceback
from datetime import datetime
from typing import List, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import FETCH_INTERVAL_MINUTES
from app.database import db
from app.scrapers import ALL_SCRAPERS

SNAPSHOT_RETENTION_DAYS = 45


class FetchScheduler:
    """定时抓取调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.is_fetching = False
        self.last_results: Dict[str, dict] = {}

    async def fetch_all_platforms(self, source: str = "scheduler"):
        """执行一次全平台全维度抓取"""
        if self.is_fetching:
            print(
                f"[{datetime.utcnow().isoformat()}] Skip {source} fetch: previous fetch still running"
            )
            return 0

        self.is_fetching = True
        try:
            print(f"[{datetime.utcnow().isoformat()}] Starting {source} fetch...")
            time_periods = ["today", "week", "month"]
            rank_types = ["hot", "rising"]
            total_count = 0

            for scraper_cls in ALL_SCRAPERS:
                scraper_name = scraper_cls.platform_key
                try:
                    async with scraper_cls() as scraper:
                        if getattr(scraper, "supports_snapshot", False):
                            total_count += await self._run_snapshot_pipeline(
                                scraper, scraper_name, rank_types, time_periods
                            )
                        else:
                            total_count += await self._run_legacy_pipeline(
                                scraper, scraper_name, rank_types, time_periods
                            )

                    self.last_results[scraper_name] = {
                        "status": "success",
                        "time": datetime.utcnow().isoformat(),
                    }
                except Exception as e:
                    error_msg = f"{e}\n{traceback.format_exc()}"
                    print(f"  [{scraper_name}] CRITICAL ERROR: {error_msg}")
                    self.last_results[scraper_name] = {
                        "status": "error",
                        "error": str(e),
                        "time": datetime.utcnow().isoformat(),
                    }

            print(
                f"[{datetime.utcnow().isoformat()}] {source.capitalize()} fetch completed. Total items: {total_count}"
            )

            try:
                deleted = await db.cleanup_snapshots(SNAPSHOT_RETENTION_DAYS)
                if deleted:
                    print(
                        f"[{datetime.utcnow().isoformat()}] Snapshot cleanup: removed {deleted} old rows "
                        f"(retention {SNAPSHOT_RETENTION_DAYS} days)"
                    )
            except Exception as exc:
                print(f"Snapshot cleanup failed: {exc}")

            return total_count
        finally:
            self.is_fetching = False

    async def _run_snapshot_pipeline(
        self,
        scraper,
        scraper_name: str,
        rank_types: List[str],
        time_periods: List[str],
    ) -> int:
        """对支持快照的平台：先存当前快照，再按时间窗口派生今日/本周/本月榜"""
        snapshots = await scraper.fetch_snapshot()
        if not snapshots:
            print(f"  [{scraper_name}] snapshot empty, skip")
            return 0

        recorded_at = datetime.utcnow()
        await db.save_snapshots(scraper.platform_key, snapshots, recorded_at=recorded_at)
        print(f"  [{scraper_name}] snapshot saved: {len(snapshots)} dramas")

        total = 0
        for rank_type in rank_types:
            for period in time_periods:
                try:
                    items = await db.derive_rankings_from_snapshots(
                        platform=scraper.platform_key,
                        snapshots=snapshots,
                        rank_type=rank_type,
                        time_period=period,
                        now=recorded_at,
                    )
                    if items:
                        count = await db.upsert_rankings(
                            scraper.platform_key, rank_type, period, items
                        )
                        total += count
                        print(f"  [{scraper_name}] {rank_type}/{period}: {count} items (snapshot-derived)")
                except Exception as exc:
                    print(f"  [{scraper_name}] {rank_type}/{period} derive failed: {exc}")
        return total

    async def _run_legacy_pipeline(
        self,
        scraper,
        scraper_name: str,
        rank_types: List[str],
        time_periods: List[str],
    ) -> int:
        """对未提供快照的平台：保留原有 fetch_hot/fetch_rising 路径"""
        total = 0
        for period in time_periods:
            for rank_type in rank_types:
                try:
                    if rank_type == "hot":
                        items = await scraper.fetch_hot(period)
                    else:
                        items = await scraper.fetch_rising(period)
                    if items:
                        count = await db.upsert_rankings(
                            scraper.platform_key, rank_type, period, items
                        )
                        total += count
                        print(f"  [{scraper_name}] {rank_type}/{period}: {count} items")
                except Exception as exc:
                    print(f"  [{scraper_name}] {rank_type}/{period} failed: {exc}")
        return total

    def start(self):
        """启动定时调度器"""
        if self.is_running:
            return

        self.scheduler.add_job(
            self.fetch_all_platforms,
            trigger=IntervalTrigger(minutes=FETCH_INTERVAL_MINUTES),
            id="drama_fetch_all",
            replace_existing=True,
            coalesce=True,  # 如果任务堆积，只执行一次
            max_instances=1,  # 同时只允许一个实例运行
            next_run_time=datetime.now().astimezone(),  # 服务启动后立即执行一次
        )
        self.scheduler.start()
        self.is_running = True
        print(f"Scheduler started. Interval: {FETCH_INTERVAL_MINUTES} minutes")

    def shutdown(self):
        """关闭调度器"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            print("Scheduler shut down")

    def get_status(self) -> dict:
        """获取调度器状态"""
        job = self.scheduler.get_job("drama_fetch_all")
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
        return {
            "is_running": self.is_running,
            "is_fetching": self.is_fetching,
            "interval_minutes": FETCH_INTERVAL_MINUTES,
            "next_run": next_run,
            "last_results": self.last_results,
        }


# 全局调度器实例
fetch_scheduler = FetchScheduler()
