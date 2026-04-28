"""探测 MoboReels、GoodShort、NetShort 真实 API"""
import re
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def req(method, url, headers=None, params=None, json_body=None):
    h = {"User-Agent": UA, "Accept": "application/json", **(headers or {})}
    try:
        if method == "GET":
            r = httpx.get(url, headers=h, params=params, follow_redirects=True, timeout=15)
        else:
            r = httpx.post(url, headers=h, json=json_body or {}, follow_redirects=True, timeout=15)
        print(f"\n{method} {url} {params or json_body} -> {r.status_code}")
        try:
            d = r.json()
            print(json.dumps(d, ensure_ascii=False, indent=2)[:3000])
        except:
            print(r.text[:300])
        return r
    except Exception as e:
        print(f"\n{method} {url} -> ERROR: {e}")
        return None

# ===== MoboReels =====
print("="*60)
print("MoboReels")
print("="*60)

MBRL_BASES = [
    "https://videoapi-hk.cdreader.vip/video",
    "https://videoapi-hk.cdreader.com/video",
    "https://kong-videoapi-shortvideo-test9.changdu.ltd/video",
]

MBRL_PATHS = [
    "/h5/series/home",
    "/h5/series/rank",
    "/h5/series/list",
    "/h5/home/index",
    "/h5/home",
    "/h5/rank",
    "/h5/series/hotList",
    "/h5/series/newList",
    "/h5/ranklist",
]

for base in MBRL_BASES:
    print(f"\n--- Testing base: {base} ---")
    for path in MBRL_PATHS[:3]:  # just first 3 per base
        req("GET", base + path, {"Referer": "https://www.moboreels.com/"})

# ===== GoodShort =====
print("\n" + "="*60)
print("GoodShort")
print("="*60)

GOOD_BASE = "https://www.goodshort.com"
GOOD_PATHS = [
    "/hwycreels/home/index",
    "/hwycreels/home/second/list",
    "/hwycreels/drama/list",
    "/hwycreels/rank/list",
]
for path in GOOD_PATHS:
    req("GET", GOOD_BASE + path, {"Referer": GOOD_BASE + "/"})

# 找 GoodShort API 基地址
print("\n=== Scanning GoodShort app.js for API base ===")
js = httpx.get("https://acfs3.goodshort.com/dist/app.49e18d6515717c31181c.js",
               headers={"User-Agent": UA}, timeout=30).text
print(f"app.js size: {len(js)}")
base_urls = re.findall(r'(?:baseURL|apiUrl|base_url|serverUrl|apiBase)\s*[:=]\s*["\`]([^"\`]{8,100})["\`]', js)
domains = re.findall(r'https?://[a-zA-Z0-9.\-]+', js)
print("Base URLs:")
for u in base_urls[:10]:
    print(" ", u)
print("Domains:")
for d in sorted(set(domains))[:20]:
    print(" ", d)

# ===== NetShort visitor login =====
print("\n" + "="*60)
print("NetShort visitor login")
print("="*60)

# First find API base from JS bundles
js_ns = httpx.get("https://netshort.com/_next/static/chunks/9605-ae018d81fefc7055.js",
                  headers={"User-Agent": UA}, timeout=30).text
base_urls_ns = re.findall(r'(?:baseURL|apiUrl|base_url|serverUrl|apiBase)\s*[:=]\s*["\`]([^"\`]{8,100})["\`]', js_ns)
domains_ns = re.findall(r'https?://[a-zA-Z0-9.\-]+(?:/[a-zA-Z0-9_\-/]{0,60})?', js_ns)
print("NetShort base URLs from JS:")
for u in base_urls_ns[:10]:
    print(" ", u)
api_domains_ns = [d for d in set(domains_ns) if any(k in d.lower() for k in ['api', 'cdn', 'short', 'drama'])]
print("API-like domains:")
for d in sorted(api_domains_ns)[:20]:
    print(" ", d)

# Try visitor login
NS_BASES = ["https://netshort.com", "https://api.netshort.com", "https://netshort-api.com"]
for base in NS_BASES:
    req("POST", base + "/web/auth/visitor_login", {}, json_body={"deviceId": "web_visitor_123", "platform": "web"})
