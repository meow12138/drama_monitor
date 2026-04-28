"""探测 FlexTV api-quick.flextv.cc"""
import re
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
API_BASE = "https://api-quick.flextv.cc"
WEB_BASE = "https://www.flextv.cc"

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": WEB_BASE + "/",
    "Origin": WEB_BASE,
    "lang": "en",
}

def get(path, params=None, extra_headers=None):
    url = API_BASE + path
    h = {**HEADERS, **(extra_headers or {})}
    try:
        r = httpx.get(url, headers=h, params=params, follow_redirects=True, timeout=15)
        print(f"\nGET {url} {params} -> {r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
        except:
            print(r.text[:500])
        return r
    except Exception as e:
        print(f"ERROR: {e}")
        return None

# 从 FlexTV 的 Nuxt bundle 中找 API 路径
print("=== Scanning FlexTV bundle for API paths ===")
js_url = "https://www.flextv.cc/_nuxt/BkrJISLG.js"
js = httpx.get(js_url, headers={"User-Agent": UA}, timeout=30).text

# 找所有字符串 (更宽松的正则)
all_strings = re.findall(r'["\`]([^"\`\n]{4,120})["\`]', js)
api_strings = [s for s in all_strings if any(k in s.lower() for k in ['/drama', '/rank', '/home', '/video', '/series', '/short', '/list', '/v1', '/v2', 'hot', 'popular'])]
print(f"Found {len(api_strings)} API-like strings:")
for s in sorted(set(api_strings))[:50]:
    print(" ", s)

# 找所有 base URL 赋值
base_patterns = re.findall(r'(?:base[Uu][Rr][Ll]|api[Uu][Rr][Ll]|apiBase|serverUrl)\s*[:=]\s*["\`]([^"\`]{8,100})["\`]', js)
print("\nBase URLs:")
for b in base_patterns[:10]:
    print(" ", b)

# 直接探测 api-quick.flextv.cc
print("\n=== Direct API probing ===")
probes = [
    ("/v1/home", None),
    ("/v1/drama/list", None),
    ("/v1/drama/hot", None),
    ("/v1/drama/rank", None),
    ("/v1/rank/hot", None),
    ("/v1/ranks", None),
    ("/v2/home", None),
    ("/api/home", None),
    ("/api/drama/list", None),
    ("/web/home", None),
    ("/web/drama/list", None),
    ("/web/rank/list", None),
    ("/", None),
]
for path, params in probes:
    get(path, params)

# 尝试带语言参数
print("\n=== With lang params ===")
get("/v1/home", {"lang": "en"})
get("/v1/drama/list", {"lang": "en", "page": 1, "pageSize": 20})
