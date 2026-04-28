"""把 Sereal+ 新快照（真实 Like/Collect 数）写入数据库"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from app.scrapers.serealplus import SerealPlusScraper
from app.database import db


async def main():
    # 初始化数据库（确保表存在）
    await db.init()

    print('Fetching Sereal+ snapshots...')
    async with SerealPlusScraper() as s:
        snaps = await s.fetch_snapshot()

    print(f'Got {len(snaps)} snapshots')

    # 写入数据库
    saved = await db.save_snapshots('serealplus', snaps)
    print(f'Saved {saved} snapshots to DB')

    # 验证写入结果
    import aiosqlite
    async with aiosqlite.connect('data/drama_monitor.db') as conn:
        conn.row_factory = aiosqlite.Row
        sql = (
            "SELECT drama_name, play_num, collect_num, tags "
            "FROM drama_snapshots "
            "WHERE platform='serealplus' "
            "ORDER BY recorded_at DESC "
            "LIMIT 5"
        )
        async with conn.execute(sql) as cur:
            rows = await cur.fetchall()

    print('\n=== 数据库中最新 5 条 ===')
    for r in rows:
        name = (r['drama_name'] or '')[:40]
        print(
            f'  {name:40s} | play={r["play_num"]:>10} | collect={r["collect_num"]:>10} '
            f'| tags={str(r["tags"] or "")[:30]}'
        )


asyncio.run(main())
