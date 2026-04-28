"""跑除 ShortMax 外的所有支持 snapshot 的 scraper（避免 ShortMax 标签索引拖慢测试）"""
import asyncio
from datetime import datetime

from app.database import db
from app.scrapers import ALL_SCRAPERS


async def main():
    await db.init()
    rank_types = ("hot", "rising")
    time_periods = ("today", "week", "month")
    for cls in ALL_SCRAPERS:
        if cls.platform_key == "shortmax":
            continue
        try:
            async with cls() as scraper:
                if not getattr(scraper, "supports_snapshot", False):
                    print(f"[{scraper.platform_key}] no snapshot support, skip")
                    continue
                snapshots = await scraper.fetch_snapshot()
                if not snapshots:
                    print(f"[{scraper.platform_key}] empty snapshot")
                    continue
                recorded_at = datetime.utcnow()
                await db.save_snapshots(scraper.platform_key, snapshots, recorded_at=recorded_at)
                print(f"[{scraper.platform_key}] snapshot={len(snapshots)}")
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
                            await db.upsert_rankings(scraper.platform_key, rt, tp, items)
                print(f"[{scraper.platform_key}] derived rankings")
        except Exception as exc:
            print(f"[{cls.platform_key}] ERROR {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
