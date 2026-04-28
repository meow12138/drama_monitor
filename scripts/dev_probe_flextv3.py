"""从 FlexTV HTML 提取嵌入的 drama 数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.flextv.cc"

html = httpx.get(BASE, headers={"User-Agent": UA}, follow_redirects=True, timeout=30).text
print(f"HTML size: {len(html)}")

# 找所有 <script> 内容
soup = BeautifulSoup(html, "html.parser")
scripts = soup.find_all("script")
print(f"Script tags: {len(scripts)}")

for i, s in enumerate(scripts):
    content = s.get_text()
    src = s.get("src", "")
    if not src and len(content) > 100:
        print(f"\n--- Script {i} (len={len(content)}) ---")
        # 找 title/image/link 相关数据
        if any(k in content for k in ['title', 'poster', 'coverUrl', 'playNum', 'series_id', 'drama_id', 'seriesId']):
            print(content[:3000])

# 找 __NUXT_DATA__ script
print("\n=== Looking for __NUXT_DATA__ or payload ===")
nuxt_data = soup.find("script", {"id": "__NUXT_DATA__"})
if nuxt_data:
    print("Found __NUXT_DATA__:", nuxt_data.string[:3000] if nuxt_data.string else nuxt_data.get_text()[:3000])

# 看 HTML 中的 img alt 和 title
print("\n=== Drama images found in HTML ===")
imgs = soup.find_all("img", src=re.compile(r"file-cdn\.flextv\.cc"))
print(f"Found {len(imgs)} images from file-cdn.flextv.cc")
for img in imgs[:10]:
    print(f"  alt={img.get('alt', '')} src={img.get('src', '')[:80]}")

# 找 JSON-LD
jsonld_scripts = soup.find_all("script", type="application/ld+json")
print(f"\nJSON-LD scripts: {len(jsonld_scripts)}")
for s in jsonld_scripts[:3]:
    print(s.get_text()[:500])

# 找 data 属性
print("\n=== Elements with data-id or data-drama-id ===")
elements_with_data = soup.find_all(attrs={"data-id": True})
print(f"data-id elements: {len(elements_with_data)}")
for el in elements_with_data[:5]:
    print(f"  tag={el.name}, data-id={el.get('data-id')}, class={el.get('class')}")

# 找 series 列表相关的元素
series_links = soup.find_all("a", href=re.compile(r"/series/"))
print(f"\nSeries links: {len(series_links)}")
for a in series_links[:10]:
    print(f"  href={a.get('href')}, text={a.get_text(strip=True)[:50]}")

# 找视频链接
video_links = soup.find_all("a", href=re.compile(r"/video/"))
print(f"\nVideo links: {len(video_links)}")
for a in video_links[:10]:
    print(f"  href={a.get('href')}, text={a.get_text(strip=True)[:50]}")

# 找包含剧名的 h2/h3
headings = soup.find_all(["h2", "h3"])
print(f"\nH2/H3 headings: {len(headings)}")
for h in headings[:20]:
    print(f"  {h.name}: {h.get_text(strip=True)[:80]}")

# 看看页面前 200 个包含 "drama" class 的元素
print("\n=== drama-related class elements ===")
drama_els = soup.find_all(class_=re.compile(r'drama|series|show|video-card|poster', re.I))
print(f"Found {len(drama_els)} elements")
for el in drama_els[:5]:
    print(f"  {el.name}.{el.get('class')} -> {str(el)[:200]}")
