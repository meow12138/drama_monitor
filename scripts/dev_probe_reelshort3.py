"""更深入探测 ReelShort - Next.js data 路径 + GET API"""
import json
import httpx

BASE = "https://www.reelshort.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BUILD_ID = "3d986ae"

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": BASE + "/",
}

def get(path, params=None):
    url = BASE + path
    r = httpx.get(url, headers=HEADERS, params=params, follow_redirects=True, timeout=15)
    print(f"\nGET {url} {params} -> {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
    except:
        print(r.text[:500])
    return r

# 1. Next.js SSR 数据端点
print("=== Next.js SSR data ===")
get(f"/_next/data/{BUILD_ID}/index.json")

# 2. getTagBook (GET)
print("\n=== getTagBook GET ===")
get("/api/video/book/getTagBook", {"language": "en", "page": 1, "page_size": 20, "tagId": ""})
get("/api/video/book/getTagBook", {"language": "en", "page": 1, "page_size": 20})

# 3. getNewTagBook (GET)
print("\n=== getNewTagBook GET ===")
get("/api/video/book/getNewTagBook", {"language": "en", "page": 1, "page_size": 20, "tagId": ""})

# 4. getRecommendBook (GET)
print("\n=== getRecommendBook GET ===")
get("/api/video/book/getRecommendBook", {"language": "en", "pageNo": 1, "pageSize": 20})

# 5. hall 端点 - 可能需要 App-Version 头
print("\n=== hall/info with extra headers ===")
h2 = {**HEADERS, "App-Version": "1.0.0", "channel": "web", "platform": "web"}
r = httpx.post(
    BASE + "/api/video/hall/info",
    headers={**h2, "Content-Type": "application/json"},
    json={"language": "en", "hallType": 1},
    follow_redirects=True, timeout=15
)
print(f"status={r.status_code}")
print(r.text[:1000])

# 6. 直接看首页的 __NEXT_DATA__
print("\n=== 读取首页 __NEXT_DATA__ ===")
html_r = httpx.get(BASE, headers=HEADERS, follow_redirects=True, timeout=20)
html = html_r.text
import re
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
if m:
    next_data = json.loads(m.group(1))
    print("keys:", list(next_data.keys()))
    props = next_data.get("props", {})
    print("props keys:", list(props.keys()))
    page_props = props.get("pageProps", {})
    print("pageProps keys:", list(page_props.keys()))
    print(json.dumps(page_props, ensure_ascii=False, indent=2)[:5000])
else:
    print("未找到 __NEXT_DATA__")
    # 找其他 JSON 数据
    for script_m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
        content = script_m.group(1).strip()
        if 'hallType' in content or 'bookList' in content or 'seriesList' in content:
            print("Found relevant script:", content[:500])
            break
