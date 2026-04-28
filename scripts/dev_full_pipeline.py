"""端到端验证：DB 迁移 + ShortMax/MoboReels/NetShort 各自一次抓取 + 派生入库"""
import asyncio
import json
import sqlite3
from datetime import datetime

from app.config import DATABASE_PATH
from app.database import db
from app.scrapers.moboreels import MoboReelsScraper
from app.scrapers.netshort import NetShortScraper
from app.scrapers.shortmax import ShortMaxScraper


async def run_scraper(scraper_cls):
    name = scraper_cls.platform_key
    async with scraper_cls() as scraper:
        snaps = await scraper.fetch_snapshot()
        if not snaps:
            print(f"[{name}] no snapshots")
            return
        recorded_at = datetime.utcnow()
        await db.save_snapshots(name, snaps, recorded_at=recorded_at)
        print(f"[{name}] snapshots saved: {len(snaps)}")
        for rt in ("hot", "rising"):
            for tp in ("today", "week", "month"):
                items = await db.derive_rankings_from_snapshots(
                    platform=name,
                    snapshots=snaps,
                    rank_type=rt,
                    time_period=tp,
                    now=recorded_at,
                )
                if items:
                    cnt = await db.upsert_rankings(name, rt, tp, items)
                    sample = items[0]
                    print(
                        f"  {rt}/{tp}: {cnt}  top={sample.drama_name!r} "
                        f"play_num={sample.play_num} collect_num={sample.collect_num} score={sample.score}"
                    )


async def main():
    await db.init()

    # 验证迁移：rankings 表有新字段
    conn = sqlite3.connect(str(DATABASE_PATH))
    cols = [row[1] for row in conn.execute("PRAGMA table_info(rankings)").fetchall()]
    print("rankings columns:", cols)
    conn.close()

    # 重置 ShortMax 之外平台的旧记录，避免叠加旧数据干扰
    for plat in ("netshort", "moboreels"):
        async with __import__("aiosqlite").connect(str(DATABASE_PATH)) as conn:
            await conn.execute(
                "DELETE FROM rankings WHERE platform=?", (plat,)
            )
            await conn.commit()

    await run_scraper(MoboReelsScraper)
    await run_scraper(NetShortScraper)
    await run_scraper(ShortMaxScraper)


if __name__ == "__main__":
    asyncio.run(main())
