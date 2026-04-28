"""验证 behavior API 是否需要 chapterId + 测试多个 drama"""
import sys
import io
import json
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
API_BASE = 'https://web-api.serealplus.com'
HEADERS = {'User-Agent': UA, 'Accept': 'application/json', 'Referer': 'https://www.sereal.com/', 'Origin': 'https://www.sereal.com'}

cid = '270506555273912320'
chapter_id = '270515207435198464'

tests = [
    f'/content/video/chapter/behavior?contentId={cid}',
    f'/content/video/chapter/behavior?contentId={cid}&chapterId=0',
    f'/content/video/chapter/behavior?contentId={cid}&chapterId={chapter_id}',
]

for path in tests:
    r = httpx.get(API_BASE + path, headers=HEADERS, follow_redirects=True, timeout=10)
    resp = r.json()
    d = resp.get('data') or {}
    thumb = d.get('thumbUpNum')
    collect = d.get('collectNum')
    print(f'{path[-80:]}')
    print(f'  code={resp.get("code")}, thumbUpNum={thumb}, collectNum={collect}')

# 测试其他几个 drama（从首页获取的）
print('\n=== Testing other dramas ===')
other_cids = [
    ('256063702376386560', 'Objection! The Legal Queen'),
    ('256817544709808128', 'My L.A. Fireman'),
    ('266571939949314048', 'Hands Off, Ex-Husband!'),
]

for other_cid, name in other_cids:
    url = f'{API_BASE}/content/video/chapter/behavior?contentId={other_cid}'
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=10)
    resp = r.json()
    d = resp.get('data') or {}
    print(f'{name}: thumbUpNum={d.get("thumbUpNum")}, collectNum={d.get("collectNum")}')
