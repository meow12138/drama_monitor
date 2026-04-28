import asyncio, aiosqlite

async def check():
    async with aiosqlite.connect('data/drama_monitor.db') as conn:
        conn.row_factory = aiosqlite.Row
        # rankings 表里的 cover_url
        sql = "SELECT drama_name, cover_url, tags FROM rankings WHERE platform='serealplus' ORDER BY rank_position LIMIT 5"
        async with conn.execute(sql) as cur:
            rows = await cur.fetchall()
        print("=== rankings ===")
        for r in rows:
            print(r['drama_name'][:30], '| cover:', (r['cover_url'] or '')[:60], '| tags:', (r['tags'] or '')[:40])

        # snapshots 表里的 cover_url
        sql2 = "SELECT drama_name, cover_url, tags FROM drama_snapshots WHERE platform='serealplus' ORDER BY recorded_at DESC LIMIT 5"
        async with conn.execute(sql2) as cur:
            rows2 = await cur.fetchall()
        print("\n=== drama_snapshots ===")
        for r in rows2:
            print(r['drama_name'][:30], '| cover:', (r['cover_url'] or '')[:60], '| tags:', (r['tags'] or '')[:40])

asyncio.run(check())
