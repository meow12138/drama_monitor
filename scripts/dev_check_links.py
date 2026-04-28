import asyncio, aiosqlite

async def check():
    async with aiosqlite.connect('data/drama_monitor.db') as conn:
        conn.row_factory = aiosqlite.Row
        sql = "SELECT platform, drama_name, link FROM rankings WHERE link IS NOT NULL AND link != '' GROUP BY platform ORDER BY platform, rank_position"
        async with conn.execute(sql) as cur:
            rows = await cur.fetchall()
    seen = {}
    for r in rows:
        p = r['platform']
        if p not in seen:
            seen[p] = True
            print(p, '|', r['drama_name'][:30], '->', r['link'][:120])

asyncio.run(check())
