"""用 Playwright 渲染 Sereal+ 详情页，提取 Like/Collect 数值"""
import asyncio
import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from app.scrapers.base import ensure_playwright_browser, close_playwright_browser

CONTENT_ID = '270506555273912320'
URL = f'https://www.sereal.com/detail/{CONTENT_ID}'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'


async def probe():
    api_calls = []

    browser = await ensure_playwright_browser()
    context = await browser.new_context(
        user_agent=UA,
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
    )

    # 拦截所有网络请求
    async def on_request(req):
        url = req.url
        if 'web-api' in url or 'api' in url.lower():
            api_calls.append(('REQ', req.method, url))

    async def on_response(resp):
        url = resp.url
        if 'web-api' in url or ('api' in url.lower() and resp.status == 200):
            try:
                body = await resp.text()
                if 'like' in body.lower() or 'collect' in body.lower():
                    api_calls.append(('RESP_LIKE', url, body[:500]))
                elif len(body) > 100:
                    api_calls.append(('RESP', url, body[:200]))
            except Exception:
                pass

    page = await context.new_page()
    page.on('request', on_request)
    page.on('response', on_response)

    print(f'Navigating to {URL} ...')
    await page.goto(URL, wait_until='networkidle', timeout=30000)
    await asyncio.sleep(3)

    # 获取渲染后的页面内容
    content = await page.content()
    print(f'Rendered HTML length: {len(content)}')

    # 查找 Like/Collect 数值
    patterns = [
        r'[Ll]ike\s*[\d.,]+[KkMm]?',
        r'[Cc]ollect\s*[\d.,]+[KkMm]?',
        r'[\d.,]+[KkMm]\s*[Ll]ike',
        r'[\d.,]+[KkMm]\s*[Cc]ollect',
    ]
    for pat in patterns:
        ms = list(re.finditer(pat, content))
        if ms:
            print(f'Pattern {pat}: {len(ms)} matches')
            for m in ms[:3]:
                snippet = content[max(0, m.start() - 50):m.end() + 50]
                print(f'  {snippet.encode("ascii", errors="replace").decode()}')

    # 查找数值字段
    for field in ['likeNum', 'likeCount', 'collectNum', 'playNum', 'playTimes']:
        ms = list(re.finditer(field, content, re.IGNORECASE))
        if ms:
            m = ms[0]
            snippet = content[max(0, m.start() - 10):m.end() + 100]
            print(f'[{field}]: {snippet.encode("ascii", errors="replace").decode()[:150]}')

    print(f'\nAPI calls intercepted: {len(api_calls)}')
    for kind, *rest in api_calls[:30]:
        if kind == 'RESP_LIKE':
            print(f'  *** {kind}: {rest[0]}')
            print(f'      {rest[1][:200]}')
        elif kind == 'REQ':
            print(f'  {rest[0]} {rest[1]}')
        else:
            print(f'  {kind}: {rest[0]}')

    await context.close()
    await close_playwright_browser()


asyncio.run(probe())
