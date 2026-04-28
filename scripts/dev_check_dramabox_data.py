import asyncio, aiosqlite

async def check():
    async with aiosqlite.connect('data/drama_monitor.db') as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT drama_name, play_num, collect_num, tags FROM drama_snapshots WHERE platform='dramabox' ORDER BY recorded_at DESC LIMIT 5"
        ) as cur:
            rows = await cur.fetchall()
    print("=== DramaBox 最新快照 ===")
    for r in rows:
        print(f"  {r['drama_name'][:30]} | play={r['play_num']} | collect={r['collect_num']} | tags={r['tags']}")

asyncio.run(check())
