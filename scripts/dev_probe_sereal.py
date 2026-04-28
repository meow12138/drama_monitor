"""诊断 Sereal+ 首页 HTML 结构（标签/链接/封面）"""
import re
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

r = httpx.get("https://www.sereal.plus", headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
              follow_redirects=True, timeout=20)
print(f"Status: {r.status_code}, size: {len(r.text)}, final_url: {r.url}")

soup = BeautifulSoup(r.text, "html.parser")

# 1. H2/H3 分区标题
headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"])]
print(f"\nH2/H3 headings ({len(headings)}):")
for h in headings[:20]:
    print(f"  {repr(h)}")

# 2. 所有链接 href 含有 drama/series/episode 的
links = soup.find_all("a", href=re.compile(r"/drama|/series|/episode|/play|/watch"))
print(f"\nDrama-like links ({len(links)}):")
for a in links[:8]:
    print(f"  href={a.get('href','')[:70]}  text={a.get_text(strip=True)[:30]}")

# 3. 所有图片 (找封面图)
imgs = soup.find_all("img", alt=True)
print(f"\nImgs with alt ({len(imgs)}):")
for img in imgs[:8]:
    print(f"  alt={img.get('alt','')[:40]}  src={str(img.get('src') or img.get('data-src') or '')[:70]}")

# 4. 所有 <a> href 含 genre/tag/category/topic
for pat in ["/genre", "/tag", "/category", "/topic", "/label", "/type", "/theme"]:
    matches = soup.find_all("a", href=re.compile(pat))
    if matches:
        print(f"\n'{pat}' links ({len(matches)}):")
        for a in matches[:3]:
            print(f"  href={a.get('href','')[:60]}  text={a.get_text(strip=True)[:30]}")

# 5. 看第一张剧卡片的完整结构
print("\n=== 首页剧卡片结构 ===")
# 找包含多张图的容器
containers = []
for div in soup.find_all(["div", "section", "ul"]):
    imgs_in = div.find_all("img")
    if len(imgs_in) >= 3:
        containers.append((len(imgs_in), div))
if containers:
    containers.sort(reverse=True)
    best = containers[0][1]
    print(best.prettify()[:3000])
