"""探测 Sereal+ API"""
import json
import re
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
API_BASE = "https://web-api.serealplus.com"
WEB_BASE = "https://www.sereal.plus"

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": WEB_BASE + "/",
    "Origin": WEB_BASE,
}

def get(url, params=None):
    try:
        r = httpx.get(url, headers=HEADERS, params=params, follow_redirects=True, timeout=15)
        print(f"\nGET {url} {params} -> {r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
        except:
            print(r.text[:500])
    except Exception as e:
        print(f"ERROR: {e}")

# 扫描 Nuxt bundle 中更多 API 路径
print("=== Scanning Sereal+ Nuxt bundle ===")
js = httpx.get(f"{WEB_BASE}/_nuxt/BHzcd6Rv.js", headers={"User-Agent": UA}, timeout=30).text
print(f"JS size: {len(js)}")

paths = re.findall(r'"(/[A-Za-z0-9_\-/]{3,80})"', js)
base_urls = re.findall(r'(?:baseURL|apiBase|base_url|serverUrl|apiUrl|baseUrl)\s*[:=]\s*["\`]([^"\`]{8,100})["\`]', js)
domains = re.findall(r'https?://[a-zA-Z0-9.\-]+(?:/[a-zA-Z0-9_\-/]{0,60})?', js)
API_KEYWORDS = ["/drama", "/rank", "/home", "/short", "/list", "/series", "/content", "/video", "/app", "/v1"]
interesting_paths = sorted(set(p for p in paths if any(k in p for k in API_KEYWORDS)))

print("\n=== Base URLs ===")
for u in sorted(set(base_urls))[:20]:
    print(" ", u)

print("\n=== Domains ===")
for d in sorted(set(domains))[:30]:
    print(" ", d)

print("\n=== API paths ===")
for p in interesting_paths[:50]:
    print(" ", p)

# 探测 web-api.serealplus.com
print("\n=== 探测 web-api.serealplus.com ===")
probes = [
    "/drama/api/front/drama/home/list",
    "/drama/api/front/drama/rank/list",
    "/drama/api/front/drama/drama/list",
    "/drama/api/front/drama/hot/list",
    "/drama/api/front/drama/list",
    "/api/drama/list",
    "/api/home",
    "/api/rank",
]
for path in probes:
    get(API_BASE + path)

# 尝试首页数据
print("\n=== 读取首页 Nuxt 数据 ===")
html = httpx.get(WEB_BASE, headers={"User-Agent": UA}, follow_redirects=True, timeout=20).text
m = re.search(r'window\.__NUXT__=(.*?)</script>', html, re.DOTALL)
if m:
    snippet = m.group(1).strip().rstrip(";")
    print("Found __NUXT__, length:", len(snippet))
    # 不能安全运行任意 JS，但可以看一下内容
    print(snippet[:2000])
