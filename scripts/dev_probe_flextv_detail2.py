"""深度解析 FlexTV 详情页 - 提取标签和互动数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup
from base64 import b64decode

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.flextv.cc"

# 用英文 Accept-Language
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

# 先从首页取一些链接
home_r = httpx.get(BASE, headers=HEADERS, follow_redirects=True, timeout=20)
home_soup = BeautifulSoup(home_r.text, "html.parser")
links = []
for a in home_soup.find_all("a", href=re.compile(r"/episodes/")):
    href = a.get("href", "")
    if href and href not in links:
        links.append(href)
        if len(links) >= 3:
            break

print(f"Found {len(links)} episode links from homepage: {links}")

for ep_path in links[:2]:
    # 尝试英文版 URL
    en_path = ep_path
    if not ep_path.startswith("/en/"):
        en_path = "/en" + ep_path

    for url in [BASE + en_path, BASE + ep_path]:
        print(f"\n{'='*60}")
        print(f"URL: {url}")
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        print(f"Status: {r.status_code}, final_url: {r.url}")
        html = r.text
        soup = BeautifulSoup(html, "html.parser")

        # 1. 解析所有 JSON-LD
        for jld in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(jld.get_text())
                t = data.get("@type", "")
                if t == "VideoObject":
                    print(f"\n  JSON-LD VideoObject:")
                    print(f"    name: {data.get('name')}")
                    print(f"    genre: {data.get('genre')}")
                    print(f"    url: {data.get('@id')}")
                    print(f"    thumbnailUrl: {str(data.get('thumbnailUrl', ''))[:80]}")
                elif t == "AggregateRating":
                    print(f"\n  JSON-LD AggregateRating:")
                    print(f"    ratingValue: {data.get('ratingValue')}")
                    print(f"    reviewCount: {data.get('reviewCount')}")
                elif t == "BreadcrumbList":
                    items = data.get("itemListElement", [])
                    print(f"\n  Breadcrumb: {[i.get('name') for i in items]}")
            except:
                pass

        # 2. 解析 __NUXT_DATA__
        nd = soup.find("script", {"id": "__NUXT_DATA__"})
        if nd:
            content = nd.get_text()
            print(f"\n  __NUXT_DATA__ len={len(content)}")
            try:
                arr = json.loads(content)
                print(f"  Array length: {len(arr)}")
                # 找含 like/collect/star 的 API key
                if isinstance(arr, list) and len(arr) > 2:
                    data_map = arr[2] if isinstance(arr[2], dict) else {}
                    print(f"  Keys in data_map: {list(data_map.keys())[:10]}")
                    for k in data_map:
                        if any(kw in k for kw in ['like', 'collect', 'star', 'favorite', 'web', 'drama', 'detail', 'series']):
                            idx = data_map[k]
                            val = arr[idx] if isinstance(idx, int) and idx < len(arr) else None
                            print(f"  key={k}, idx={idx}, val={str(val)[:200]}")
            except Exception as e:
                print(f"  Parse error: {e}")
                # 直接找数字
                for m in re.finditer(r'"(?:like|collect|star|favorite|view)(?:Count|_count|Num|_num)"\s*:\s*(\d+)', content):
                    print(f"  Count match: {m.group(0)}")

        # 3. 找可视化数字元素（像截图中的 17.7K）
        print("\n  All text matching K/M numbers:")
        for el in soup.find_all(True):
            text = el.get_text(strip=True)
            if re.match(r'^\d+\.?\d*[KkMm]$', text):
                print(f"    {el.name}.{el.get('class', [])}: '{text}'")

        print("\n  First 3000 chars of NUXT_DATA:")
        nd2 = soup.find("script", {"id": "__NUXT_DATA__"})
        if nd2:
            print(nd2.get_text()[:3000])
        break  # 只测第一个URL格式
