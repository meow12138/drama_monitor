"""探测 ReelShort 的具体 API 端点"""
import json
import httpx

BASE = "https://www.reelshort.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": BASE + "/",
}

def get(path, params=None):
    url = BASE + path
    try:
        r = httpx.get(url, headers=HEADERS, params=params, follow_redirects=True, timeout=15)
        print(f"\nGET {url} params={params} -> {r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        except:
            print(r.text[:500])
        return r
    except Exception as e:
        print(f"\nGET {url} -> ERROR: {e}")
        return None

def post(path, payload=None):
    url = BASE + path
    try:
        r = httpx.post(url, headers={**HEADERS, "Content-Type": "application/json"},
                       json=payload or {}, follow_redirects=True, timeout=15)
        print(f"\nPOST {url} -> {r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        except:
            print(r.text[:500])
        return r
    except Exception as e:
        print(f"\nPOST {url} -> ERROR: {e}")
        return None

print("=== /api/video/hall/info ===")
get("/api/video/hall/info")

print("\n=== /api/video/hall/info with hallType ===")
for ht in [1, 2, 3, 4, 5]:
    get("/api/video/hall/info", {"hallType": ht})

print("\n=== /api/video/hall/webSeeAll ===")
get("/api/video/hall/webSeeAll")
get("/api/video/hall/webSeeAll", {"hallType": 1, "pageNo": 1, "pageSize": 20})
get("/api/video/hall/webSeeAll", {"hallType": 2, "pageNo": 1, "pageSize": 20})

print("\n=== /api/video/book/getTagList ===")
get("/api/video/book/getTagList")

print("\n=== /api/video/book/getRecommendBook ===")
get("/api/video/book/getRecommendBook")
get("/api/video/book/getRecommendBook", {"pageNo": 1, "pageSize": 20})

print("\n=== /api/video/book/getNewTagBook ===")
get("/api/video/book/getNewTagBook", {"pageNo": 1, "pageSize": 20})

print("\n=== /stories/ranking ===")
get("/stories/ranking")
