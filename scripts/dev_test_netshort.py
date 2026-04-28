"""测试 NetShort 真实抓取 + 派生榜单"""
import asyncio
import json
from datetime import datetime

from app.database import db
from app.scrapers.netshort import NetShortScraper


async def main() -> None:
    await db.init()
    async with NetShortScraper() as scraper:
        snapshots = await scraper.fetch_snapshot()
        print(f"snapshots: {len(snapshots)}")
        if snapshots:
            print(json.dumps(snapshots[0].model_dump(), ensure_ascii=False, indent=2))

        if not snapshots:
            return

        recorded_at = datetime.utcnow()
        await db.save_snapshots(scraper.platform_key, snapshots, recorded_at=recorded_at)
        for rt in ("hot", "rising"):
            for tp in ("today", "week", "month"):
                items = await db.derive_rankings_from_snapshots(
                    platform=scraper.platform_key,
                    snapshots=snapshots,
                    rank_type=rt,
                    time_period=tp,
                    now=recorded_at,
                )
                if items:
                    cnt = await db.upsert_rankings(scraper.platform_key, rt, tp, items)
                    print(
                        f"{rt}/{tp} -> upserted {cnt}, top: {items[0].drama_name} "
                        f"(score={items[0].score}, tags={items[0].tags})"
                    )


if __name__ == "__main__":
    asyncio.run(main())
