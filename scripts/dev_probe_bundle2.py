"""搜索 JS bundle 中 likeCountBase/playTimes 的使用方式"""
import sys
import io
import re
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
r = httpx.get('https://www.sereal.com/_nuxt/BHzcd6Rv.js', headers={'User-Agent': UA}, timeout=30)
js = r.text
print(f'Bundle size: {len(js)}')

# 搜索 likeCountBase/likeNum/playTimes 上下文
for term in ['likeCountBase', 'likeNum', 'playTimes', 'collectNum', 'thumbUp', 'likeCount']:
    ms = list(re.finditer(term, js, re.IGNORECASE))
    if ms:
        print(f'\n=== {term}: {len(ms)} occurrences ===')
        for m in ms[:3]:
            ctx = js[max(0, m.start() - 100):m.end() + 200]
            safe = ctx.encode('ascii', errors='replace').decode()
            print(f'  ...{safe}...')

# 找 like 计数的显示逻辑
print('\n=== Looking for like count display format (K/M) ===')
# 查找格式化函数
for term in ['0.6M', '1e3', '1e6', '1000', 'K", "M"', 'format']:
    ms = list(re.finditer(re.escape(term), js, re.IGNORECASE))
    if ms and len(ms) < 20:
        print(f'\n{term}: {len(ms)} occurrences')
        for m in ms[:2]:
            ctx = js[max(0, m.start() - 50):m.end() + 100]
            safe = ctx.encode('ascii', errors='replace').decode()
            print(f'  {safe}')

# 找 thumbUp 相关
print('\n=== thumbUp context ===')
for m in re.finditer('thumbUp', js):
    ctx = js[max(0, m.start() - 100):m.end() + 200]
    safe = ctx.encode('ascii', errors='replace').decode()
    print(f'  {safe[:200]}')
    print()
