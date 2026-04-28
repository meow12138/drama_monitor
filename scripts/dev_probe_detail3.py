"""分析详情页 Nuxt 数组中的 API 缓存数据 + 查找 JS bundle 中的 API 路径"""
import asyncio
import sys
import io
import re
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from app.scrapers.serealplus import SerealPlusScraper
import httpx

CONTENT_ID = '270506555273912320'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'


def deref(arr, ref, depth=0):
    if depth > 5:
        return ref
    if isinstance(ref, int) and 0 <= ref < len(arr):
        val = arr[ref]
        if isinstance(val, int) and val != ref:
            return deref(arr, val, depth + 1)
        return val
    return ref


def deep_deref(arr, val, depth=0):
    """递归解引用整个对象"""
    if depth > 10:
        return val
    if isinstance(val, int) and 0 <= val < len(arr):
        return deep_deref(arr, arr[val], depth + 1)
    if isinstance(val, dict):
        return {k: deep_deref(arr, v, depth + 1) for k, v in val.items()}
    if isinstance(val, list):
        return [deep_deref(arr, item, depth + 1) for item in val]
    return val


async def probe():
    async with SerealPlusScraper() as s:
        url = f'https://www.sereal.com/detail/{CONTENT_ID}'
        html = await s.fetch_html(url, use_proxy=False)

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
                    break
            except Exception:
                pass

        if not arr:
            print('No Nuxt array found')
            return

        # 查看 Element 3 (API 缓存容器)
        el3 = arr[3]
        print('=== Element 3 keys ===')
        for cache_key, cache_val_ref in el3.items():
            cache_val = deref(arr, cache_val_ref)
            print(f'Key: {cache_key}')
            if isinstance(cache_val, dict) or isinstance(cache_val, list):
                resolved = deep_deref(arr, cache_val)
                print(f'  Value: {json.dumps(resolved, ensure_ascii=False)[:1000]}')
            else:
                print(f'  Value: {cache_val}')
            print()

        # 查找 JS bundle 文件（script src）
        print('\n=== JS Bundle files ===')
        for sc in soup.find_all('script', src=True):
            src = sc.get('src', '')
            print(f'  {src}')

    # 下载主 JS bundle，搜索 API 路径
    print('\n=== Searching JS bundle for API paths ===')
    bundle_urls = []
    async with SerealPlusScraper() as s:
        html = await s.fetch_html(f'https://www.sereal.com/detail/{CONTENT_ID}', use_proxy=False)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for sc in soup.find_all('script', src=True):
            src = sc.get('src', '')
            if src and '_nuxt/' in src:
                bundle_urls.append(src)

    print(f'Found {len(bundle_urls)} bundle files')

    # 下载最大的 bundle（通常是主入口），搜索 detail 相关 API 路径
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for bu in bundle_urls[:10]:
            full_url = f'https://www.sereal.com{bu}' if bu.startswith('/') else bu
            try:
                resp = await client.get(full_url, headers={'User-Agent': UA})
                js = resp.text
                # 找 drama detail 相关路径
                paths = re.findall(r'"(/[a-zA-Z0-9_/\-]{5,80})"', js)
                detail_paths = [p for p in paths if 'detail' in p.lower() or 'like' in p.lower() or 'collect' in p.lower()]
                if detail_paths:
                    print(f'\nBundle {bu}: size={len(js)}, detail paths:')
                    for p in sorted(set(detail_paths))[:20]:
                        print(f'  {p}')
                else:
                    print(f'Bundle {bu}: size={len(js)}, no detail paths')
            except Exception as e:
                print(f'Error downloading {bu}: {e}')


asyncio.run(probe())
