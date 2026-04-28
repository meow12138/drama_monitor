"""探测 Sereal+ 详情页数据结构"""
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

def deref(arr, ref):
    if isinstance(ref, int) and 0 <= ref < len(arr):
        return arr[ref]
    return ref


async def probe():
    async with SerealPlusScraper() as s:
        url = f'https://www.sereal.com/detail/{CONTENT_ID}'
        html = await s.fetch_html(url, use_proxy=False)
        print(f'HTML length: {len(html)}')

        # 查找 like/collect 相关字段
        patterns = [
            'likeNum', 'collectNum', 'likeCount', 'collectCount',
            'subscribeNum', 'followNum', 'subscribeCount', 'playNum',
            'viewNum', 'viewCount', 'fansNum', 'favoriteNum',
        ]
        for pat in patterns:
            ms = list(re.finditer(pat, html, re.IGNORECASE))
            if ms:
                m = ms[0]
                snippet = html[max(0, m.start() - 20):m.end() + 150]
                safe = snippet.encode('ascii', errors='replace').decode()
                print(f'[{pat}] x{len(ms)}: {safe[:200]}')

        # 找 Nuxt 数据数组（脚本文件）
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.find_all('script', src=False)
        print(f'\nTotal inline scripts: {len(scripts)}')
        for i, sc in enumerate(scripts):
            txt = sc.get_text()
            if len(txt) > 500:
                safe = txt[:300].encode('ascii', errors='replace').decode()
                print(f'Script {i} (len={len(txt)}): {safe[:200]}')

        # 尝试解析所有 JSON 脚本
        print('\n=== Trying to parse scripts as JSON ===')
        for i, sc in enumerate(scripts):
            txt = sc.get_text().strip()
            if not txt:
                continue
            try:
                data = json.loads(txt)
                if isinstance(data, list) and len(data) > 5:
                    print(f'Script {i}: JSON array, len={len(data)}')
                    # 查找里面的 like/collect
                    for j, el in enumerate(data):
                        if isinstance(el, dict):
                            keys = set(str(k).lower() for k in el.keys())
                            if any('like' in k or 'collect' in k for k in keys):
                                print(f'  Element {j}: keys={list(el.keys())[:10]}')
                                # 尝试解引用
                                for k, v in el.items():
                                    if 'like' in k.lower() or 'collect' in k.lower():
                                        resolved = deref(data, v)
                                        print(f'    {k}={v} -> {resolved}')
                elif isinstance(data, dict):
                    print(f'Script {i}: JSON dict, keys={list(data.keys())[:10]}')
            except Exception:
                pass


asyncio.run(probe())
