"""在所有 Nuxt chunk 文件中搜索 Like/collect 计数相关代码"""
import sys
import io
import re
import httpx
import asyncio

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from app.scrapers.serealplus import SerealPlusScraper
from bs4 import BeautifulSoup

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

async def probe():
    async with SerealPlusScraper() as s:
        html = await s.fetch_html('https://www.sereal.com/detail/270506555273912320', use_proxy=False)

    soup = BeautifulSoup(html, 'html.parser')

    # 收集所有 script src
    chunk_urls = []
    for sc in soup.find_all('script', src=True):
        src = sc.get('src', '')
        if src:
            if src.startswith('/'):
                chunk_urls.append(f'https://www.sereal.com{src}')
            elif src.startswith('http'):
                chunk_urls.append(src)

    print(f'Found {len(chunk_urls)} chunk files')
    for u in chunk_urls:
        print(f'  {u}')

    # 下载每个 chunk 并搜索关键词
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for url in chunk_urls:
            try:
                r = await client.get(url, headers={'User-Agent': UA})
                js = r.text
                # 搜索关键词
                terms = ['likeNum', 'likeCount', 'playTimes', 'collectNum', 'playNum', 'thumbUpNum',
                         'likeCountBase', 'formatCount', 'formatLike', '0.6M', '0.6K', 'K", "M"']
                found = []
                for term in terms:
                    if term.lower() in js.lower():
                        found.append(term)
                if found:
                    print(f'\n*** {url} (size={len(js)}): found {found}')
                    # 打印上下文
                    for term in found[:3]:
                        ms = list(re.finditer(re.escape(term), js, re.IGNORECASE))
                        for m in ms[:2]:
                            ctx = js[max(0, m.start() - 100):m.end() + 200]
                            safe = ctx.encode('ascii', errors='replace').decode()
                            print(f'  {safe[:300]}')
            except Exception as e:
                print(f'Error for {url}: {e}')


asyncio.run(probe())
