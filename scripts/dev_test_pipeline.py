"""临时联调脚本：验证 ShortMax 快照 → 派生榜单"""
import asyncio
import json

from app.database import db
from app.scrapers.shortmax import ShortMaxScraper


async def main() -> None:
    await db.init()
    async with ShortMaxScraper() as scraper:
        snapshots = await scraper.fetch_snapshot()
        await db.save_snapshots(scraper.platform_key, snapshots)
        print(
            json.dumps(
                {
                    "snapshot_count": len(snapshots),
                    "first": snapshots[0].model_dump() if snapshots else None,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

        for rank_type in ("hot", "rising"):
            for time_period in ("today", "week", "month"):
                items = await db.derive_rankings_from_snapshots(
                    platform=scraper.platform_key,
                    snapshots=snapshots,
                    rank_type=rank_type,
                    time_period=time_period,
                )
                top = items[0].model_dump() if items else None
                print(rank_type, time_period, len(items), top)


if __name__ == "__main__":
    asyncio.run(main())
