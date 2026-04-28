"""深度挖 Sereal+ 页面内嵌 JSON 数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
r = httpx.get("https://www.sereal.plus", headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
              follow_redirects=True, timeout=20)
html = r.text
soup = BeautifulSoup(html, "html.parser")

# 1. 检查所有 inline script 内容
scripts = soup.find_all("script", src=False)
print(f"Inline scripts: {len(scripts)}")
for i, s in enumerate(scripts):
    content = s.get_text()
    if "serealshort" in content or "cover" in content.lower() or "drama" in content.lower():
        print(f"\n--- Script {i} (len={len(content)}) ---")
        print(content[:3000])

# 2. 找所有包含 serealshort.com 的字符串
sereal_refs = re.findall(r'["\']([^"\']*serealshort[^"\']{0,200})["\']', html)
print(f"\n\nserealshort.com refs in HTML ({len(sereal_refs)}):")
for ref in sereal_refs[:15]:
    print(f"  {ref[:120]}")

# 3. 找 drama/series/content ID 格式
# serealshort.com cover URL 里有 ID: /cover/{id}
cover_ids = re.findall(r'/content/cover/([a-z0-9]{10,30})', html)
print(f"\nCover IDs found ({len(cover_ids)}): {cover_ids[:10]}")

# 4. 寻找带 data- 属性的剧名卡片
data_drama = soup.find_all(attrs={"data-id": True})
print(f"\nElements with data-id: {len(data_drama)}")
for el in data_drama[:5]:
    print(f"  {el.name}, data-id={el.get('data-id')}, class={el.get('class','')}")

# 5. 看 img 元素的所有属性（找真实图片 URL）
imgs_with_alt = soup.find_all("img", alt=lambda a: a and len(a) > 3)
print(f"\nImgs with real alt ({len(imgs_with_alt)}):")
for img in imgs_with_alt[:10]:
    attrs = {k: str(v)[:80] for k, v in img.attrs.items()}
    print(f"  alt={img.get('alt','')[:40]}: {attrs}")

# 6. 看 Nuxt state（__NUXT__ 配置之外的数据）
m = re.search(r'window\.__NUXT__\s*=\s*(\{.*?\})\s*;?\s*window\.__NUXT__', html, re.DOTALL)
if m:
    print(f"\n__NUXT__ block: {m.group(1)[:500]}")

# 找所有 JSON-like 嵌入数据
json_blocks = re.findall(r'<script[^>]*>window\[([^\]]+)\]\s*=\s*(.{10,500}?)</script>', html, re.DOTALL)
print(f"\nwindow[] assignments: {len(json_blocks)}")
for k, v in json_blocks[:3]:
    print(f"  {k}: {v[:200]}")

# 7. 用 web-api.serealplus.com 直接请求首页数据
print("\n=== 尝试 web-api.serealplus.com ===")
api_probes = [
    "https://web-api.serealplus.com/drama/api/front/drama/recommend/list",
    "https://web-api.serealplus.com/drama/api/front/drama/hot/list",
    "https://web-api.serealplus.com/drama/api/front/home/index",
    "https://web-api.serealplus.com/drama/api/front/drama/newest/list",
]
with httpx.Client(headers={
    "User-Agent": UA,
    "Origin": "https://www.sereal.com",
    "Referer": "https://www.sereal.com/",
    "language": "en",
    "locale": "en",
}, follow_redirects=True, timeout=10) as c:
    for url in api_probes:
        try:
            rr = c.get(url, params={"page": 1, "pageSize": 10, "language": "en", "locale": "en"})
            txt = rr.text[:200].replace("\n", " ")
            print(f"  {rr.status_code} {url.split('/')[-1]}: {txt}")
        except Exception as e:
            print(f"  ERR {url}: {e}")
