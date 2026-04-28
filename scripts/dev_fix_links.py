"""排查 GoodShort / MoboReels / ReelShort 正确 URL 格式"""
import re
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def get(url):
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as c:
        r = c.get(url)
    print(f"  {r.status_code}  {r.url}")
    if r.status_code == 200:
        print(f"  OK (size={len(r.text)})")
    return r

# ===== GoodShort =====
print("=== GoodShort ===")
# 原始链接 404
get("https://www.goodshort.com/dramas/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454")
# 尝试不同路径
get("https://www.goodshort.com/playlets/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454")
get("https://www.goodshort.com/book/31000881454")
get("https://www.goodshort.com/watch/31000881454")
# 直接用 sourceId 搜索正确 URL
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as c:
    r = c.get("https://www.goodshort.com")
    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all("a", href=re.compile(r"/31000881454"))
    print(f"\n  Links for 31000881454: {[a.get('href') for a in links[:5]]}")
    # 找所有带书号的链接
    sample = soup.find_all("a", href=re.compile(r"/\d{10,}"))
    print(f"  Sample drama links: {[a.get('href') for a in sample[:5]]}")

# ===== MoboReels =====
print("\n=== MoboReels ===")
get("https://www.moboreels.com/series/41896322")
get("https://www.moboreels.com/dramas/41896322")
get("https://www.moboreels.com/drama/41896322")
# 从首页找正确路径
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as c:
    r = c.get("https://www.moboreels.com")
    soup = BeautifulSoup(r.text, "html.parser")
    all_links = soup.find_all("a", href=True)
    drama_links = [a.get("href") for a in all_links if a.get("href") and "series" in a.get("href","").lower()]
    print(f"  Drama links on homepage: {drama_links[:5]}")

# ===== ReelShort =====
print("\n=== ReelShort ===")
get("https://www.reelshort.com/episodes/episode-1-the-alpha-s-dead-luna-k2bzfcqg5e")
# ReelShort chapter_id 可能过期，找正确格式
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as c:
    import json
    r = c.get("https://www.reelshort.com/api/video/book/getTagBook", params={"language": "en", "page": 1, "page_size": 5})
    data = r.json()
    books = (data.get("data") or {}).get("books") or []
    for b in books[:3]:
        chap_id = b.get("chapter_id", "")
        title = b.get("book_title", "")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")[:60]
        url = f"https://www.reelshort.com/episodes/episode-1-{slug}-{chap_id}"
        print(f"  title={title[:30]}, chapter_id={chap_id}")
        r2 = c.get(url, follow_redirects=True, timeout=10)
        print(f"  -> {r2.status_code} {url[:90]}")
