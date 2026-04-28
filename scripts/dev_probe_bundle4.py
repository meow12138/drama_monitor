"""查找 Like/Collect 按钮的数据来源"""
import sys
import io
import re
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
r = httpx.get('https://www.sereal.com/_nuxt/BHzcd6Rv.js', headers={'User-Agent': UA}, timeout=30)
js = r.text

# 查找 Like/Collect 按钮渲染
print('=== "like" label context ===')
for m in re.finditer(r'"[Ll]ike"', js):
    ctx = js[max(0, m.start() - 200):m.end() + 300]
    safe = ctx.encode('ascii', errors='replace').decode()
    print(f'{safe[:400]}')
    print('---')

# 查找 playTimes/playNum 上下文
print('\n=== playTimes/playNum/likeNum in bundle ===')
for term in ['playTimes', 'playNum', 'likeNum', 'collectNum', 'likeCount']:
    ms = list(re.finditer(term, js, re.IGNORECASE))
    if ms:
        print(f'\n--- {term}: {len(ms)} occurrences ---')
        for m in ms[:2]:
            ctx = js[max(0, m.start() - 100):m.end() + 200]
            safe = ctx.encode('ascii', errors='replace').decode()
            print(f'  {safe[:300]}')

# 搜索数字格式化函数
print('\n=== Number format (K/M display) ===')
# 找 formatCount 或类似函数
for term in ['formatCount', 'formatNum', 'numFormat', 'formatLike', 'formatPlay']:
    ms = list(re.finditer(term, js, re.IGNORECASE))
    if ms:
        print(f'\n--- {term}: {len(ms)} ---')
        for m in ms[:2]:
            ctx = js[max(0, m.start() - 50):m.end() + 200]
            safe = ctx.encode('ascii', errors='replace').decode()
            print(f'  {safe[:250]}')

# 找 .1K .1M 格式化
for term in ['toFixed(1)', 'toFixed(2)', '+ "K"', '+ "M"', '"K"', '"M"']:
    ms = list(re.finditer(re.escape(term), js))
    if ms:
        print(f'\n--- {term}: {len(ms)} ---')
        for m in ms[:3]:
            ctx = js[max(0, m.start() - 100):m.end() + 100]
            safe = ctx.encode('ascii', errors='replace').decode()
            print(f'  {safe[:200]}')
