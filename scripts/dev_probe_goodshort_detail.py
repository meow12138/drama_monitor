"""探查 GoodShort 详情页 Views / Followers 数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.goodshort.com"

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/html, */*",
    "Referer": BASE + "/",
    "Content-Type": "application/json",
}

# 测试：Blood and Bones of the Disowned Daughter
SLUG = "blood-and-bones-of-the-disowned-daughter-31001113972"
BOOK_ID = "31001113972"
detail_url = f"{BASE}/drama/{SLUG}"

print(f"=== 详情页 HTML: {detail_url} ===")
r = httpx.get(detail_url, headers={"User-Agent": UA}, follow_redirects=True, timeout=15)
print(f"Status: {r.status_code}, size: {len(r.text)}")
html = r.text
soup = BeautifulSoup(html, "html.parser")

# 1. 找 Views / Followers 数字
print("\n--- Views/Followers 数值 ---")
for el in soup.find_all(string=re.compile(r"Views|Followers|Fans", re.I)):
    parent = el.parent
    sibling = parent.find_next_sibling() if parent else None
    print(f"  '{el.strip()[:30]}' | sibling={sibling.get_text(strip=True)[:20] if sibling else None}")

# 2. 大数值
print("\n--- K/M 格式数字 ---")
for el in soup.find_all(string=re.compile(r"\d+\.?\d*[KkMm]")):
    parent = el.parent
    if parent and parent.name not in ["script", "style"]:
        print(f"  '{el.strip()[:30]}' | {parent.name}.{parent.get('class', [])}")

# 3. 探测 API 端点
print("\n=== API 端点探测 ===")
# 已知主页 API
for path, payload in [
    ("/hwycreels/book/detail", {"bookId": BOOK_ID}),
    ("/hwycreels/book/info", {"bookId": BOOK_ID}),
    ("/hwycreels/drama/detail", {"bookId": BOOK_ID}),
    ("/hwycreels/drama/detail", {"sourceId": BOOK_ID}),
    ("/hwycreels/book/detail", {"sourceId": BOOK_ID}),
    ("/hwycreels/bookdetail/get", {"bookId": BOOK_ID}),
]:
    try:
        resp = httpx.post(BASE + path, headers=HEADERS, json=payload, timeout=8)
        if resp.status_code != 404:
            print(f"  [{resp.status_code}] POST {path}: {resp.text[:200]}")
    except Exception as e:
        print(f"  ERR {path}: {e}")

# 4. GET 探测
for path in [
    f"/hwycreels/book/{BOOK_ID}",
    f"/hwycreels/drama/{BOOK_ID}",
    f"/hwycreels/book/detail/{BOOK_ID}",
]:
    try:
        resp = httpx.get(BASE + path, headers={"User-Agent": UA}, timeout=8)
        if resp.status_code != 404:
            print(f"  [{resp.status_code}] GET {path}: {resp.text[:200]}")
    except:
        pass

# 5. 找 JS 里的 API 调用
print("\n=== 页面 JS 里的 API 路径 ===")
for script in soup.find_all("script", src=False):
    content = script.get_text()
    if "hwycreels" in content or "view" in content.lower():
        paths = re.findall(r'["\`](/hwycreels[^"\`\s]{3,80})["\`]', content)
        if paths:
            print(f"  hwycreels paths: {paths[:10]}")
        # 找 viewCount / followCount
        for kw in ["viewCount", "followCount", "viewNum", "followNum", "fansNum"]:
            if kw in content:
                print(f"  Found '{kw}' in inline script")
