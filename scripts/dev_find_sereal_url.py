"""系统地找 Sereal+ drama 详情页 URL 格式"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.sereal.com"

# 测试内容 ID
CONTENT_ID = "251334496623009792"
CONTENT_NAME = "Cohabitating Lover"
SLUG = re.sub(r"[^a-z0-9]+", "-", CONTENT_NAME.lower()).strip("-")

# 1. 批量测试各种路径
print("=== URL 格式探测 ===")
test_paths = [
    # 带 contentId
    f"/drama/{CONTENT_ID}",
    f"/watch/{CONTENT_ID}",
    f"/play/{CONTENT_ID}",
    f"/episode/{CONTENT_ID}",
    f"/show/{CONTENT_ID}",
    f"/detail/{CONTENT_ID}",
    f"/video/{CONTENT_ID}",
    f"/content/{CONTENT_ID}",
    f"/movie/{CONTENT_ID}",
    # 带 slug
    f"/{SLUG}",
    f"/drama/{SLUG}",
    f"/show/{SLUG}",
    f"/watch/{SLUG}",
    # 带 slug + id
    f"/drama/{SLUG}-{CONTENT_ID}",
    f"/{SLUG}-{CONTENT_ID}",
    # browse 变体
    f"/browse/{CONTENT_ID}",
    f"/browse/drama/{CONTENT_ID}",
]
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=10) as c:
    for path in test_paths:
        r = c.get(BASE + path)
        note = " <-- 200!" if r.status_code == 200 else ""
        print(f"  {r.status_code}  {path}{note}")

# 2. 从 JS bundle 找路由定义
print("\n=== 从 Nuxt bundle 找路由定义 ===")
r = httpx.get("https://www.sereal.plus", headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
soup = BeautifulSoup(r.text, "html.parser")
# 找所有 _nuxt JS
script_srcs = [s.get("src") for s in soup.find_all("script", src=True) if "/_nuxt/" in (s.get("src") or "")]
print(f"Nuxt JS chunks: {script_srcs}")

# 找 inline script 里的路由
for s in soup.find_all("script", src=False):
    content = s.get_text()
    if "routes" in content.lower() and "component" in content.lower():
        # 找路径定义
        paths_in_routes = re.findall(r'path:\s*["\']([^"\']{2,60})["\']', content)
        if paths_in_routes:
            print(f"Routes in inline script: {paths_in_routes[:20]}")
            break

# 3. 抓取 bundle 找路由
if script_srcs:
    for src in script_srcs[:2]:
        url = "https://www.sereal.plus" + src if src.startswith("/") else src
        js = httpx.get(url, headers={"User-Agent": UA}, timeout=20).text
        # 找路径定义
        paths = re.findall(r'path:\s*["\`]([^"\`]{2,60})["\`]', js)
        interesting = [p for p in paths if any(k in p.lower() for k in ['drama', 'series', 'video', 'watch', 'play', 'episode', 'content'])]
        if interesting:
            print(f"\nDrama routes in {src}: {interesting[:20]}")

# 4. 尝试 web-api 找详情
print("\n=== 尝试 web-api 找 drama detail ===")
API_BASE = "https://web-api.serealplus.com"
for path in [
    f"/drama/api/front/drama/detail?contentId={CONTENT_ID}",
    f"/drama/api/front/drama/detail?id={CONTENT_ID}",
    f"/drama/api/front/content/detail?id={CONTENT_ID}",
]:
    try:
        rr = httpx.get(API_BASE + path, headers={"User-Agent": UA, "Referer": BASE + "/", "Origin": BASE}, timeout=8)
        print(f"  {rr.status_code} {path}: {rr.text[:100]}")
    except Exception as e:
        print(f"  ERR {path}: {e}")
