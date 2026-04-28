"""探测 GoodShort 翻页和完整剧目列表"""
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.goodshort.com"
HEADERS = {"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json", "Referer": BASE + "/"}

def post(path, payload=None):
    r = httpx.post(BASE + path, headers=HEADERS, json=payload or {}, timeout=15)
    print(f"\nPOST {path} {payload} -> {r.status_code}")
    try:
        d = r.json()
        print(json.dumps(d, ensure_ascii=False, indent=2)[:2000])
        return d
    except:
        print(r.text[:300])
        return None

# 尝试 second/list 带 columnId
print("=== home/second/list with columnId ===")
# 知道 Top in GoodShort = 1523, Hot List = 1524
for col_id in [1523, 1524, 1509, 1529]:
    for page in [1, 2]:
        d = post("/hwycreels/home/second/list", {"columnId": col_id, "page": page, "pageSize": 20})
        if d and d.get("data"):
            items = d.get("data", {}).get("items") or d.get("data") or []
            if isinstance(items, list):
                print(f"  Got {len(items)} items")
                if items:
                    print(f"  First: {items[0].get('bookName')} | view={items[0].get('viewCount')}")

# 尝试带 channelId 参数
print("\n=== home/second/list with channelId ===")
for channel_id in [1, 2, 3, 10, 100]:
    d = post("/hwycreels/home/second/list", {"channelId": channel_id, "columnId": 1523, "page": 1, "pageSize": 20})
    if d and d.get("data"):
        print(f"  channelId={channel_id}: {d}")

# 查看 vendor.js 里的 second/list 参数
print("\n=== vendor.js second/list usage ===")
import re
js = httpx.get("https://acfs3.goodshort.com/dist/app.49e18d6515717c31181c.js",
               headers={"User-Agent": UA}, timeout=30).text
matches = re.findall(r'second[^;]{0,300}', js)
for m in matches[:5]:
    print(m[:200])

# 找有没有 playlets/list 或 dramas/list 这种分页接口
print("\n=== Probe more paths ===")
for path in [
    "/hwycreels/playlets/list",
    "/hwycreels/dramas/list",
    "/hwycreels/book/list",
    "/hwycreels/home/list",
    "/hwycreels/home/column/list",
]:
    d = post(path, {"page": 1, "pageSize": 20})
