"""深度探测 ReelShort POST API"""
import json
import httpx

BASE = "https://www.reelshort.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": BASE + "/",
    "Origin": BASE,
}

def post(path, payload=None):
    url = BASE + path
    try:
        r = httpx.post(url, headers=HEADERS, json=payload or {}, follow_redirects=True, timeout=15)
        print(f"\nPOST {url} payload={payload} -> {r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
        except:
            print(r.text[:500])
        return r
    except Exception as e:
        print(f"\nPOST {url} -> ERROR: {e}")
        return None

def get(path, params=None):
    url = BASE + path
    try:
        r = httpx.get(url, headers=HEADERS, params=params, follow_redirects=True, timeout=15)
        print(f"\nGET {url} {params} -> {r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
        except:
            print(r.text[:500])
        return r
    except Exception as e:
        print(f"\nGET {url} -> ERROR: {e}")
        return None

print("=== hall/info POST ===")
post("/api/video/hall/info", {"language": "en", "hallType": 1})
post("/api/video/hall/info", {"language": "en"})

print("\n=== hall/webSeeAll POST ===")
post("/api/video/hall/webSeeAll", {"language": "en", "hallType": 1, "pageNo": 1, "pageSize": 20})
post("/api/video/hall/webSeeAll", {"language": "en", "hallType": 2, "pageNo": 1, "pageSize": 20})
post("/api/video/hall/webSeeAll", {"language": "en", "hallType": 3, "pageNo": 1, "pageSize": 20})

print("\n=== getTagList POST ===")
post("/api/video/book/getTagList", {"language": "en"})

print("\n=== getNewTagBook POST ===")
post("/api/video/book/getNewTagBook", {"language": "en", "page": 1, "page_size": 20, "tagId": ""})

print("\n=== getTagBook POST ===")
post("/api/video/book/getTagBook", {"language": "en", "page": 1, "page_size": 20, "tagId": ""})

print("\n=== getRecommendBook POST ===")
post("/api/video/book/getRecommendBook", {"language": "en", "pageNo": 1, "pageSize": 20})

print("\n=== getNewTagList POST ===")
post("/api/video/book/getNewTagList", {"language": "en"})

# 尝试带 token header 的版本
print("\n=== 带 token 尝试 ===")
get("/api/video/book/getTagList", {"language": "en"})
