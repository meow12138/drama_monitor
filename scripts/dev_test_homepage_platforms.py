"""验证 5 个新平台的通用首页解析"""
import asyncio
import json
from datetime import datetime

from app.database import db
from app.scrapers.flextv import FlexTVScraper
from app.scrapers.goodshort import GoodShortScraper
from app.scrapers.melolo import MeloloScraper
from app.scrapers.reelshort import ReelShortScraper
from app.scrapers.serealplus import SerealPlusScraper


SCRAPERS = [
    ReelShortScraper,
    SerealPlusScraper,
    FlexTVScraper,
    GoodShortScraper,
    MeloloScraper,
]


async def run_one(scraper_cls):
    name = scraper_cls.platform_key
    try:
        async with scraper_cls() as scraper:
            snaps = await scraper.fetch_snapshot()
            print(f"[{name}] snapshots: {len(snaps)}")
            if snaps:
                top = snaps[0].model_dump()
                print(f"  top: {top.get('drama_name')!r} link={top.get('link')}")
                print(f"  cover: {top.get('cover_url')}")
                recorded_at = datetime.utcnow()
                await db.save_snapshots(name, snaps, recorded_at=recorded_at)
                for rt in ("hot", "rising"):
                    items = await db.derive_rankings_from_snapshots(
                        platform=name,
                        snapshots=snaps,
                        rank_type=rt,
                        time_period="today",
                        now=recorded_at,
                    )
                    if items:
                        await db.upsert_rankings(name, rt, "today", items)
                        print(f"  {rt}/today upserted {len(items)}, top={items[0].drama_name}")
    except Exception as exc:
        print(f"[{name}] ERROR: {exc!r}")


async def main():
    await db.init()
    for cls in SCRAPERS:
        await run_one(cls)


if __name__ == "__main__":
    asyncio.run(main())
