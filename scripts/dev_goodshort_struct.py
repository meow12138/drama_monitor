"""查看 GoodShort 完整非 banner 栏目 item 结构"""
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.goodshort.com"
HEADERS = {"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json", "Referer": BASE + "/"}

r = httpx.post(BASE + "/hwycreels/home/index", headers=HEADERS, json={}, timeout=15)
data = r.json()
columns = data["data"]["pageColumns"]

# 打印非 banner 栏目的第一个 item 完整结构
for col in columns:
    if col["style"] != "BANNER" and col.get("items"):
        print(f"\n=== Column: {col['name']} (style={col['style']}) ===")
        print(json.dumps(col["items"][0], ensure_ascii=False, indent=2))
        break

# 打印所有 columns 的所有 items
print("\n=== All columns summary ===")
for col in columns:
    items = col.get("items", [])
    print(f"\nColumn: {col['name']} ({col['style']}) - {len(items)} items")
    for item in items[:3]:
        cover = item.get("bannerUrl") or item.get("coverUrl") or item.get("bookCover") or item.get("poster") or item.get("cover") or "NO_COVER"
        print(f"  {item.get('bookName')} | viewCount={item.get('viewCount')} | cover_field={[k for k in item if 'url' in k.lower() or 'cover' in k.lower() or 'img' in k.lower() or 'poster' in k.lower() or 'pic' in k.lower()]}")
