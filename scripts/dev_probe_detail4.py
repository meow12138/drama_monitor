"""查找详情页 HTML 中所有大数字和 K/M 格式数据"""
import asyncio
import sys
import io
import re
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from app.scrapers.serealplus import SerealPlusScraper
from bs4 import BeautifulSoup

CONTENT_ID = '270506555273912320'


async def probe():
    async with SerealPlusScraper() as s:
        url = f'https://www.sereal.com/detail/{CONTENT_ID}'
        html = await s.fetch_html(url, use_proxy=False)
        print(f'HTML length: {len(html)}')

        # 查找 K/M 格式数字
        km_matches = list(re.finditer(r'[\d.]+\s*[KkMm]\b', html))
        print(f'K/M pattern occurrences: {len(km_matches)}')
        if km_matches:
            for m in km_matches[:10]:
                ctx = html[max(0, m.start() - 50):m.end() + 80]
                safe = ctx.encode('ascii', errors='replace').decode()
                print(f'  {safe}')

        # 查找所有大数字 (>1000)
        big_nums = list(re.finditer(r'\b\d{4,}\b', html))
        print(f'\nBig number (4+ digits) occurrences: {len(big_nums)}')

        # 解析 Nuxt 数组，找第一个章节的完整字段
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', src=False)
        arr = None
        for sc in scripts:
            txt = sc.get_text().strip()
            try:
                data = json.loads(txt)
                if isinstance(data, list) and len(data) > 100:
                    arr = data
                    break
            except Exception:
                pass

        if arr:
            # Element 20 onwards - chapter elements
            el20 = arr[20]
            print(f'\n=== Element 20 (first chapter): ===')
            print(f'Keys: {sorted(el20.keys()) if isinstance(el20, dict) else type(el20)}')
            if isinstance(el20, dict):
                for k, v in el20.items():
                    resolved = arr[v] if isinstance(v, int) and 0 <= v < len(arr) else v
                    print(f'  {k}={v} -> {repr(resolved)[:80]}')

            # 打印前25个元素的值
            print('\n=== Array[0..25] values ===')
            for i in range(25):
                el = arr[i]
                if not isinstance(el, dict):
                    print(f'[{i}]: {repr(el)[:60]}')

            # 检查 _errors key 中是否有 likeNum 数据
            el3 = arr[3]
            print('\n=== Element 3 - errors key ===')
            if isinstance(el3, dict) and '_errors' in el3:
                err_ref = el3.get('_errors')
                if isinstance(err_ref, int):
                    err_val = arr[err_ref] if 0 <= err_ref < len(arr) else None
                    print(f'_errors -> index {err_ref} -> {repr(err_val)[:200]}')

            # 找第三个 API 缓存 key (3F6wvzLnB5iple9iJ474EGFM3u1yP1qYeNNpUF7cpPg)
            print('\n=== Third API cache key ===')
            if '3F6wvzLnB5iple9iJ474EGFM3u1yP1qYeNNpUF7cpPg' in html:
                idx = html.index('3F6wvzLnB5iple9iJ474EGFM3u1yP1qYeNNpUF7cpPg')
                snippet = html[idx:idx + 200]
                safe = snippet.encode('ascii', errors='replace').decode()
                print(safe)


asyncio.run(probe())
