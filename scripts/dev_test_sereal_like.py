"""测试 SerealPlusScraper.fetch_snapshot，打印前5条"""
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from app.scrapers.serealplus import SerealPlusScraper


async def main():
    print('Starting fetch_snapshot test...')
    async with SerealPlusScraper() as s:
        snaps = await s.fetch_snapshot()
    print(f'\nTotal snapshots: {len(snaps)}')
    print('\n=== 前5条 ===')
    for i, snap in enumerate(snaps[:5]):
        print(f'[{i+1}] {snap.drama_name[:45]}')
        print(f'     play_num={snap.play_num}, collect_num={snap.collect_num}')
        print(f'     tags={snap.tags}')
        print(f'     link={snap.link}')
    
    # 统计有真实数据的条目
    real_data = [s for s in snaps if (s.play_num or 0) > 1000]
    print(f'\n有真实 like 数据（>1000）的条目: {len(real_data)} / {len(snaps)}')
    if real_data:
        top3 = sorted(real_data, key=lambda x: x.play_num or 0, reverse=True)[:3]
        print('Top 3 by play_num:')
        for snap in top3:
            print(f'  {snap.drama_name[:40]:40s} play={snap.play_num}, collect={snap.collect_num}')


asyncio.run(main())
