"""分析 JS bundle 中的 API 路径"""
import sys
import io
import re
import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
r = httpx.get('https://www.sereal.com/_nuxt/BHzcd6Rv.js', headers={'User-Agent': UA}, timeout=30)
js = r.text
print(f'Bundle size: {len(js)}')

# 找所有 API 路径模式
pattern = r'"(/[a-zA-Z0-9_/\-]{4,100})"'
all_paths = re.findall(pattern, js)
all_paths_uniq = sorted(set(all_paths))
print(f'Total unique paths: {len(all_paths_uniq)}')

# 筛选有趣的
keywords = ['like', 'collect', 'play', 'view', 'count', 'num', 'stat', 'metric', 'info', 'detail']
for p in all_paths_uniq:
    pl = p.lower()
    if any(k in pl for k in keywords):
        print(f'  {p}')

print('\n=== All paths with /content/ or /drama/ ===')
for p in all_paths_uniq:
    if '/content/' in p or '/drama/' in p or '/video/' in p:
        print(f'  {p}')
