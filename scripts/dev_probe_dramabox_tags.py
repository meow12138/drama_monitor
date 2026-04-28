"""诊断 DramaBox 标签缺失问题"""
import re
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

r = httpx.get("https://www.dramabox.com", headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
print(f"Status: {r.status_code}, size: {len(r.text)}")

if r.status_code != 200:
    print("无法访问首页，跳过")
    exit()

soup = BeautifulSoup(r.text, "html.parser")

# 1. 找 /drama/ 链接
drama_links = soup.find_all("a", href=re.compile(r"/drama/"))
print(f"\n/drama/ links: {len(drama_links)}")
for a in drama_links[:3]:
    print(f"  href={a.get('href')[:60]}  text={a.get_text(strip=True)[:40]}")

# 2. 找所有 genre/tag 类链接
for pattern in ["/genre", "/tag", "/category", "/topic", "/label", "/shelf"]:
    links = soup.find_all("a", href=re.compile(pattern))
    if links:
        print(f"\n'{pattern}' links ({len(links)}):")
        for a in links[:3]:
            print(f"  href={a.get('href')[:60]}  text={a.get_text(strip=True)[:30]}")

# 3. 找一个 drama 卡片，看完整结构
print("\n=== 第一个 drama 卡片结构 ===")
if drama_links:
    a = drama_links[0]
    # 上溯到卡片容器
    container = a
    for _ in range(5):
        container = container.parent
        if container and len(container.find_all("a")) >= 2:
            break
    print(container.prettify()[:1500])

# 4. 找所有 h2/h3 标题
headings = [(t.name, t.get_text(strip=True)[:40]) for t in soup.find_all(["h2", "h3"])]
print(f"\nH2/H3 headings ({len(headings)}):")
for h in headings[:15]:
    print(f"  {h}")

# 5. 看第一张完整卡片的 HTML（含 img alt 和所有 class）
print("\n=== 第一个 drama/ 锚点的父容器 ===")
if drama_links:
    a = drama_links[0]
    li = a.find_parent("li") or a.find_parent("div") or a.parent
    print(li.prettify()[:2000] if li else "no parent found")
