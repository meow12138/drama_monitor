"""深度探测 GoodShort - 获取所有栏目及播放数据"""
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.goodshort.com"
HEADERS = {
    "User-Agent": UA, "Accept": "application/json",
    "Content-Type": "application/json", "Referer": BASE + "/",
}

def post(path, payload=None):
    r = httpx.post(BASE + path, headers=HEADERS, json=payload or {}, timeout=15)
    print(f"\nPOST {path} -> {r.status_code}")
    try:
        return r.json()
    except:
        print(r.text[:300])
        return None

# 获取完整首页数据
print("=== Full home/index ===")
data = post("/hwycreels/home/index")
if data and data.get("data"):
    columns = data["data"]["pageColumns"]
    print(f"Total columns: {len(columns)}")
    for col in columns:
        print(f"\n  Column: id={col['id']}, name={col['name']}, style={col['style']}, items={len(col.get('items', []))}")
        items = col.get("items", [])
        if items:
            item = items[0]
            print(f"    First item: bookName={item.get('bookName')}, viewCount={item.get('viewCount')}, "
                  f"sourceId={item.get('sourceId')}, tags={[t['name'] for t in item.get('tagsList', [])[:3]]}")

# 获取更多页面列表
print("\n=== hwycreels/home/second/list (with columnId) ===")
if data and data.get("data"):
    for col in data["data"]["pageColumns"]:
        if col.get("style") in ["HOT_RANK", "HOT_LIST", "LIST", "RANK", "HORIZONTAL"]:
            r2 = post("/hwycreels/home/second/list", {
                "columnId": col["id"],
                "page": 1,
                "pageSize": 20,
            })
            if r2:
                print(f"\nColumn {col['name']} (id={col['id']}, style={col['style']}):")
                print(json.dumps(r2, ensure_ascii=False, indent=2)[:2000])

# 专门找热榜
print("\n=== Probing hot/rank endpoints ===")
for path in [
    "/hwycreels/rank/hot",
    "/hwycreels/drama/hot",
    "/hwycreels/home/hot",
    "/hwycreels/drama/rank",
    "/hwycreels/rank",
]:
    r2 = post(path, {"page": 1, "pageSize": 20})
    if r2:
        print(f"\n{path}:", json.dumps(r2, ensure_ascii=False, indent=2)[:300])
