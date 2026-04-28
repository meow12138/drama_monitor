"""按调度器流程跑一次 ShortMax 快照入库 + 派生今日/本周/本月榜"""
import asyncio
from datetime import datetime

from app.database import db
from app.scrapers.shortmax import ShortMaxScraper


async def main() -> None:
    await db.init()
    rank_types = ["hot", "rising"]
    time_periods = ["today", "week", "month"]
    async with ShortMaxScraper() as scraper:
        snapshots = await scraper.fetch_snapshot()
        if not snapshots:
            print("no snapshots")
            return
        recorded_at = datetime.utcnow()
        await db.save_snapshots(scraper.platform_key, snapshots, recorded_at=recorded_at)
        print(f"snapshot saved: {len(snapshots)}")
        total = 0
        for rt in rank_types:
            for tp in time_periods:
                items = await db.derive_rankings_from_snapshots(
                    platform=scraper.platform_key,
                    snapshots=snapshots,
                    rank_type=rt,
                    time_period=tp,
                    now=recorded_at,
                )
                if items:
                    cnt = await db.upsert_rankings(scraper.platform_key, rt, tp, items)
                    total += cnt
                    print(f"{rt}/{tp}: {cnt}")
        print(f"total: {total}")


if __name__ == "__main__":
    asyncio.run(main())
