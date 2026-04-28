import asyncio, aiosqlite, httpx

async def check():
    async with aiosqlite.connect('data/drama_monitor.db') as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT drama_name, link FROM rankings WHERE platform='dramabox' AND link IS NOT NULL AND link != '' LIMIT 5"
        ) as cur:
            rows = await cur.fetchall()
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=10) as c:
        for r in rows:
            try:
                resp = c.get(r['link'])
                print(f"[{resp.status_code}] {r['drama_name'][:30]}")
                print(f"       {r['link']}")
            except Exception as e:
                print(f"[ERR] {r['drama_name'][:30]}: {e}")

asyncio.run(check())
