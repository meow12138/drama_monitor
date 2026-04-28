"""深度探测 GoodShort API"""
import re
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
GOOD_BASE = "https://www.goodshort.com"
GOOD_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": GOOD_BASE + "/",
    "Origin": GOOD_BASE,
}

def post(url, payload=None):
    try:
        r = httpx.post(url, headers=GOOD_HEADERS, json=payload or {}, follow_redirects=True, timeout=15)
        print(f"\nPOST {url} {payload} -> {r.status_code}")
        try:
            d = r.json()
            print(json.dumps(d, ensure_ascii=False, indent=2)[:3000])
        except:
            print(r.text[:500])
        return r
    except Exception as e:
        print(f"\nPOST {url} -> ERROR: {e}")
        return None

def get(url, params=None, headers=None):
    h = {**GOOD_HEADERS, **(headers or {})}
    try:
        r = httpx.get(url, headers=h, params=params, follow_redirects=True, timeout=15)
        print(f"\nGET {url} {params} -> {r.status_code}")
        try:
            d = r.json()
            print(json.dumps(d, ensure_ascii=False, indent=2)[:3000])
        except:
            print(r.text[:500])
        return r
    except Exception as e:
        print(f"\nGET {url} -> ERROR: {e}")
        return None

print("=== GoodShort POST APIs ===")
post(GOOD_BASE + "/hwycreels/home/index", {})
post(GOOD_BASE + "/hwycreels/home/index", {"page": 1, "pageSize": 20})
post(GOOD_BASE + "/hwycreels/home/second/list", {"page": 1, "pageSize": 20})
post(GOOD_BASE + "/hwycreels/drama/list", {"page": 1, "pageSize": 20})

# 也试试 api.xintaicz.cn
print("\n=== api.xintaicz.cn ===")
XINTAI_BASE = "https://api.xintaicz.cn"
for path in ["/hwycreels/home/index", "/home/index", "/v1/home", "/drama/list", "/rank/list"]:
    post(XINTAI_BASE + path, {"page": 1, "pageSize": 20})

# 扫描 vendor.js 找更多 API 信息
print("\n=== Scanning GoodShort vendor.js ===")
js = httpx.get("https://acfs3.goodshort.com/dist/vendor.950ad56d017427ff71aa.js",
               headers={"User-Agent": UA}, timeout=30).text
print(f"vendor.js size: {len(js)}")

# 找 API 路径
paths = re.findall(r'["\`](/hwycreels[^"\`]{1,80})["\`]', js)
print("hwycreels paths:")
for p in sorted(set(paths))[:30]:
    print(" ", p)

base_urls = re.findall(r'(?:baseURL|apiUrl|base_url|serverUrl|apiBase|baseUrl)\s*[:=]\s*["\`]([^"\`]{8,100})["\`]', js)
print("\nBase URLs:")
for u in base_urls[:10]:
    print(" ", u)

# 找 xintaicz
xintai_refs = re.findall(r'[^"\`\n]{0,30}xintai[^"\`\n]{0,80}', js)
print("\nxintaicz references:")
for r in xintai_refs[:10]:
    print(" ", r)
