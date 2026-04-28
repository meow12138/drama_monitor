"""测试新实现的 API 爬虫"""
import asyncio
import json


async def test_reelshort():
    from app.scrapers.reelshort import ReelShortScraper
    print("\n" + "="*60)
    print("ReelShort API Test")
    print("="*60)
    async with ReelShortScraper() as s:
        snaps = await s.fetch_snapshot()
    print(f"Snapshots: {len(snaps)}")
    if snaps:
        s0 = snaps[0]
        print(f"Top: {s0.drama_name} | play_num={s0.play_num} | collect_num={s0.collect_num} | tags={s0.tags}")
        print(f"link: {s0.link}")
        print(f"cover: {s0.cover_url}")
    return snaps


async def test_goodshort():
    from app.scrapers.goodshort import GoodShortScraper
    print("\n" + "="*60)
    print("GoodShort API Test")
    print("="*60)
    async with GoodShortScraper() as s:
        snaps = await s.fetch_snapshot()
    print(f"Snapshots: {len(snaps)}")
    if snaps:
        # 按 play_num 排序展示
        top = sorted(snaps, key=lambda x: x.play_num or 0, reverse=True)[:5]
        for i, snap in enumerate(top, 1):
            print(f"#{i}: {snap.drama_name} | viewCount={snap.play_num} | tags={snap.tags}")
            print(f"    link: {snap.link}")
    return snaps


async def test_flextv():
    from app.scrapers.flextv import FlexTVScraper
    print("\n" + "="*60)
    print("FlexTV Snapshot Test")
    print("="*60)
    async with FlexTVScraper() as s:
        snaps = await s.fetch_snapshot()
    print(f"Snapshots: {len(snaps)}")
    if snaps:
        for snap in snaps[:5]:
            print(f"  {snap.drama_name} | link={snap.link} | cover={'YES' if snap.cover_url else 'NO'}")
    return snaps


async def main():
    await test_reelshort()
    await test_goodshort()
    await test_flextv()

if __name__ == "__main__":
    asyncio.run(main())
