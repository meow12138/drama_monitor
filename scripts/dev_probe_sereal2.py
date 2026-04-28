"""深度分析 Sereal+ 剧卡片结构"""
import re
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

r = httpx.get("https://www.sereal.plus", headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
              follow_redirects=True, timeout=20)
soup = BeautifulSoup(r.text, "html.parser")
print(f"Final URL: {r.url}, size: {len(r.text)}")

# 1. 找 "Most Trending" 分区
h2 = soup.find(lambda t: t.name in ["h2","h3"] and "Trending" in t.get_text())
print(f"\n'Most Trending' heading: {h2}")
if h2:
    # 上溯找含图的容器
    node = h2
    for _ in range(8):
        node = node.parent
        if not node:
            break
        imgs = node.find_all("img", alt=True)
        real_imgs = [img for img in imgs if img.get("alt","").strip() and not img.get("src","").startswith("data:")]
        print(f"  level {_}: {node.name}.{node.get('class',[])} | imgs={len(imgs)}, real_imgs={len(real_imgs)}")
        if real_imgs:
            print("  First real img:", real_imgs[0].get("alt"), "|", str(real_imgs[0].get("src",""))[:80])
            # 看该卡片容器完整结构
            card_parent = real_imgs[0].find_parent(class_=True)
            print("\n  Card HTML:")
            print(card_parent.prettify()[:1500] if card_parent else "no parent")
            break

# 2. 找所有含 serealshort.com 图片链接
print("\n=== serealshort.com 图片 (含父级结构) ===")
sereal_imgs = soup.find_all("img", src=re.compile(r"serealshort\.com"))
print(f"Found {len(sereal_imgs)} cover images")
for img in sereal_imgs[:3]:
    parent = img.find_parent(class_=True)
    # 向上找链接
    a_parent = img.find_parent("a")
    print(f"\n  alt={img.get('alt','')[:40]}")
    print(f"  src={img.get('src','')[:80]}")
    print(f"  a_parent: {a_parent.get('href','NO_LINK')[:60] if a_parent else 'NO ANCHOR PARENT'}")
    print(f"  container class: {parent.get('class','') if parent else 'none'}")
    # 找附近所有 a 标签
    if parent:
        nearby_links = parent.find_all("a", href=True)
        print(f"  nearby links: {[a.get('href','')[:50] for a in nearby_links[:4]]}")

# 3. 看所有链接
all_links = [(a.get("href",""), a.get_text(strip=True)[:20]) for a in soup.find_all("a", href=True)]
print(f"\n=== All links ({len(all_links)}) ===")
for href, text in all_links[:30]:
    print(f"  {href[:70]}  [{text}]")
