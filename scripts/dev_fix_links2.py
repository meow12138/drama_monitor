"""确认 GoodShort 和 ReelShort 正确 URL 格式"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# ===== GoodShort =====
print("=== GoodShort URL 格式探查 ===")
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=20) as c:
    # 尝试不同路径
    for path in [
        "/dramas/playlets/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454",
        "/playlets/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454",
        "/video/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454",
        "/31000881454",
        "/dramas/31000881454",
        "/book/31000881454",
        "/watch/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454",
        "/short/31000881454",
    ]:
        try:
            r = c.get(f"https://www.goodshort.com{path}", timeout=8)
            print(f"  {r.status_code}  {path}")
        except Exception as e:
            print(f"  ERR  {path}: {e}")

    # 看首页 JS 里的路由
    r = c.get("https://acfs3.goodshort.com/dist/app.49e18d6515717c31181c.js", timeout=20)
    js = r.text
    routes = re.findall(r'path:\s*["\']([^"\']{3,60})["\']', js)
    print(f"\n  Routes in app.js: {routes[:20]}")

# ===== ReelShort =====
print("\n=== ReelShort URL 格式探查 ===")
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=20) as c:
    # 从首页提取实际链接
    r = c.get("https://www.reelshort.com")
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    links = list(set(a.get("href") for a in soup.find_all("a", href=True)
                     if a.get("href","").startswith("/") and len(a.get("href","")) > 5))
    print(f"  Links on homepage: {sorted(links)[:20]}")

    # 从 __NEXT_DATA__ 找链接格式
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if m:
        nd = json.loads(m.group(1))
        # 找书的链接
        def find_links(obj, depth=0):
            if depth > 6:
                return []
            found = []
            if isinstance(obj, str) and obj.startswith("/") and ("book" in obj or "drama" in obj or "episode" in obj):
                found.append(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    found.extend(find_links(v, depth+1))
            elif isinstance(obj, list):
                for v in obj:
                    found.extend(find_links(v, depth+1))
            return found
        nd_links = find_links(nd)
        print(f"  __NEXT_DATA__ drama links: {nd_links[:10]}")

    # 尝试不同 URL 格式
    book_id_from_db = "68e9aa284838ef5d700ef20a"  # MongoDB _id
    t_book_id = "200000000000000355"
    for path in [
        f"/drama/{t_book_id}",
        f"/drama/{book_id_from_db}",
        f"/book/{book_id_from_db}",
        f"/episodes/{book_id_from_db}",
        f"/series/{book_id_from_db}",
        f"/watch/{book_id_from_db}",
    ]:
        try:
            r2 = c.get(f"https://www.reelshort.com{path}", timeout=8)
            print(f"  {r2.status_code}  {path}")
        except Exception as e:
            print(f"  ERR  {path}")
