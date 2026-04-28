"""深入分析 JS bundle 中 likeCountBase 的使用 + 找到 behaviorData API"""
import sys
import io
import re
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
r = httpx.get('https://www.sereal.com/_nuxt/BHzcd6Rv.js', headers={'User-Agent': UA}, timeout=30)
js = r.text
print(f'Bundle size: {len(js)}')

# 找 likeCountBase 上下文
print('\n=== likeCountBase contexts ===')
for m in re.finditer('likeCountBase', js, re.IGNORECASE):
    ctx = js[max(0, m.start() - 200):m.end() + 300]
    safe = ctx.encode('ascii', errors='replace').decode()
    print(f'  {safe[:400]}')
    print()

# 找 behaviorData 或 behavior data API
print('\n=== behaviorData/fetchBehavior context ===')
for term in ['behaviorData', 'fetchBehavior', 'behavior/get', 'chapter/behavior', 'behavior']:
    ms = list(re.finditer(term, js, re.IGNORECASE))
    if ms and len(ms) < 30:
        print(f'\n--- {term}: {len(ms)} occurrences ---')
        for m in ms[:3]:
            ctx = js[max(0, m.start() - 50):m.end() + 200]
            safe = ctx.encode('ascii', errors='replace').decode()
            print(f'  {safe[:300]}')

# 找 GET_CONTENT_DETAIL 或 detail 请求
print('\n=== Content detail API definitions ===')
for term in ['GET_CONTENT', 'CONTENT_DETAIL', 'GET_DRAMA', 'DRAMA_DETAIL', 'VIDEO_DETAIL']:
    ms = list(re.finditer(term, js, re.IGNORECASE))
    if ms:
        print(f'\n--- {term}: {len(ms)} ---')
        for m in ms[:2]:
            ctx = js[max(0, m.start() - 30):m.end() + 200]
            safe = ctx.encode('ascii', errors='replace').decode()
            print(f'  {safe[:200]}')
