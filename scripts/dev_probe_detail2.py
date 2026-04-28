"""深入分析 Sereal+ 详情页 Nuxt 数组 - 找到 likeNum 真实值"""
import asyncio
import sys
import io
import re
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from app.scrapers.serealplus import SerealPlusScraper

CONTENT_ID = '270506555273912320'


def deref(arr, ref):
    if isinstance(ref, int) and 0 <= ref < len(arr):
        return arr[ref]
    return ref


async def probe():
    async with SerealPlusScraper() as s:
        url = f'https://www.sereal.com/detail/{CONTENT_ID}'
        html = await s.fetch_html(url, use_proxy=False)
        print(f'HTML length: {len(html)}')

        # 找最大 inline script 解析为数组
        import re as _re
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', src=False)

        arr = None
        for sc in scripts:
            txt = sc.get_text().strip()
            if len(txt) < 1000:
                continue
            try:
                data = json.loads(txt)
                if isinstance(data, list) and len(data) > 100:
                    arr = data
                    print(f'Found Nuxt array, len={len(arr)}')
                    break
            except Exception:
                pass

        if not arr:
            print('No Nuxt array found')
            return

        # 打印前 30 个元素的类型/值
        print('\n=== First 30 elements ===')
        for i in range(min(30, len(arr))):
            el = arr[i]
            if isinstance(el, dict):
                print(f'[{i}] dict, keys={list(el.keys())[:8]}')
            elif isinstance(el, str) and len(el) > 20:
                print(f'[{i}] str: {el[:60]}')
            else:
                print(f'[{i}] {type(el).__name__}: {repr(el)[:60]}')

        # 找 Element 4 的全部字段
        print('\n=== Element 4 (main content?) ===')
        el4 = arr[4] if len(arr) > 4 else None
        if isinstance(el4, dict):
            print(f'Keys: {sorted(el4.keys())}')
            for k, v in el4.items():
                resolved = deref(arr, v)
                print(f'  {k}={v} -> {repr(resolved)[:80]}')

        # 找包含 likeNum 且 likeNum 有真实值的元素
        print('\n=== Elements with non-None likeNum ===')
        for i, el in enumerate(arr):
            if isinstance(el, dict) and 'likeNum' in el:
                like_val = deref(arr, el.get('likeNum'))
                collect_val = deref(arr, el.get('collectNum')) if 'collectNum' in el else 'N/A'
                like_base = deref(arr, el.get('likeCountBase')) if 'likeCountBase' in el else 'N/A'
                if like_val is not None:
                    cid = deref(arr, el.get('id')) or deref(arr, el.get('contentId'))
                    cname = deref(arr, el.get('contentName')) or deref(arr, el.get('name'))
                    print(f'[{i}] id={cid}, name={str(cname)[:30]}, likeNum={like_val}, collectNum={collect_val}, likeCountBase={like_base}')

        # 查找 collectNum
        print('\n=== Elements with collectNum ===')
        for i, el in enumerate(arr):
            if isinstance(el, dict) and 'collectNum' in el:
                val = deref(arr, el.get('collectNum'))
                print(f'[{i}] collectNum -> {val}, keys={list(el.keys())[:5]}')
                if i > 20:
                    print('(truncated...)')
                    break

        # 看看 script 4 (window.__NUXT__) 的完整内容
        print('\n=== window.__NUXT__ config ===')
        for sc in scripts:
            txt = sc.get_text()
            if '__NUXT__' in txt:
                print(txt[:800])
                break


asyncio.run(probe())
