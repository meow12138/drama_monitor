"""探测 FlexTV 剧集详情页的标签、点赞、收藏数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.flextv.cc"

EPISODE_URLS = [
    "/episodes/episode-1-choosing-the-devil-over-you-r0OB5MkZXA",
    "/episodes/episode-1-justice-in-blood-dubbed-mEZqoBAz8Q",
    "/episodes/episode-1-engineering-my-kingdom-MPOxyPVzqX",
]

for ep_url in EPISODE_URLS:
    full_url = BASE + ep_url
    print(f"\n{'='*60}")
    print(f"URL: {full_url}")
    r = httpx.get(full_url, headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
    print(f"Status: {r.status_code}, size: {len(r.text)}")
    
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. 找 __NUXT_DATA__
    nd = soup.find("script", {"id": "__NUXT_DATA__"})
    if nd:
        content = nd.get_text()
        print(f"\n__NUXT_DATA__ len={len(content)}")
        # 找点赞/收藏数字
        nums = re.findall(r'\d+\.?\d*[KkMm]?', content[:5000])
        # 找 API 路径
        api_paths = re.findall(r'"(/(?:web|api)[^"]{3,80})"', content[:5000])
        print("API paths:", api_paths[:10])
        # 找剧数据
        for kw in ['likeCount', 'like_count', 'collectCount', 'collect_count', 'starCount', 'star_count',
                   'favoriteCount', 'favorite_count', 'tags', 'genres', 'labels']:
            idx = content.find(kw)
            if idx != -1:
                print(f"  {kw} found at {idx}: ...{content[idx:idx+80]}...")
    
    # 2. 找标签 - 各种可能的容器
    print("\n--- Tag elements ---")
    # 尝试不同的标签选择器
    for selector in [
        "a[href*='/drama/']",
        "a[href*='/genre/']",
        "a[href*='/tag/']",
        "a[href*='/topics/']",
        ".tag", ".tags", ".genre", ".label",
        "[class*='tag']", "[class*='genre']", "[class*='label']",
    ]:
        els = soup.select(selector)
        if els:
            print(f"  {selector}: {len(els)} elements")
            for el in els[:5]:
                print(f"    text={el.get_text(strip=True)[:40]}, href={el.get('href', '')[:60]}")
    
    # 3. 找点赞/收藏数字 - 找带有 K/M 后缀的数字
    print("\n--- Count elements (17.7K, 23.3K style) ---")
    for el in soup.find_all(string=re.compile(r'\d+\.?\d*[KkMm]')):
        parent = el.parent
        if parent:
            print(f"  text={el.strip()[:30]}, parent={parent.name}.{parent.get('class', [])}")
    
    # 4. 找所有含数字的 span/div 紧靠图标的
    print("\n--- Numeric spans near icons ---")
    for el in soup.find_all(['span', 'div'], string=re.compile(r'^\s*\d+\.?\d*[KkMm]?\s*$')):
        print(f"  {el.name}.{el.get('class', [])}: '{el.get_text(strip=True)}'")
    
    # 5. 找 JSON-LD
    for jld in soup.find_all("script", type="application/ld+json"):
        print(f"\n  JSON-LD: {jld.get_text()[:500]}")
    
    # 只处理第一个 URL 以免太慢
    break
