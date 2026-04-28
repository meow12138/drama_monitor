"""验证 Sereal+ drama 详情 URL 格式 + 解析 Nuxt 数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.sereal.com"

r = httpx.get("https://www.sereal.plus", headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
              follow_redirects=True, timeout=20)
soup = BeautifulSoup(r.text, "html.parser")

# 找 Script 4 (最大的 inline script)
scripts = [s for s in soup.find_all("script", src=False) if len(s.get_text()) > 5000]
print(f"Large scripts: {len(scripts)}, sizes: {[len(s.get_text()) for s in scripts]}")

# 解析最大的那个 (Nuxt 数据数组)
nuxt_script = max(scripts, key=lambda s: len(s.get_text()))
content = nuxt_script.get_text().strip()
print(f"\nNuxt script len: {len(content)}")
print("Starts with:", content[:100])

# 尝试解析为 JSON
try:
    arr = json.loads(content)
    print(f"Array length: {len(arr)}")
except Exception as e:
    print(f"JSON parse error: {e}")
    arr = None

if arr:
    # 找 contentId / contentName / url 结构
    drama_records = []
    for i, el in enumerate(arr):
        if isinstance(el, dict) and "contentId" in el and "contentName" in el:
            content_id_ref = el.get("contentId")
            content_name_ref = el.get("contentName")
            url_ref = el.get("url")
            class_ref = el.get("classList")
            
            content_id = arr[content_id_ref] if isinstance(content_id_ref, int) and content_id_ref < len(arr) else ""
            content_name = arr[content_name_ref] if isinstance(content_name_ref, int) and content_name_ref < len(arr) else ""
            cover_url = arr[url_ref] if isinstance(url_ref, int) and url_ref < len(arr) else ""
            
            tags = []
            if isinstance(class_ref, int) and class_ref < len(arr):
                class_list = arr[class_ref]
                if isinstance(class_list, list):
                    for cls_ref in class_list:
                        if isinstance(cls_ref, int) and cls_ref < len(arr):
                            cls_obj = arr[cls_ref]
                            if isinstance(cls_obj, dict):
                                name_ref2 = cls_obj.get("name")
                                if isinstance(name_ref2, int) and name_ref2 < len(arr):
                                    name = arr[name_ref2]
                                    if isinstance(name, str) and len(name) > 1 and not name.isdigit():
                                        tags.append(name)
            
            if content_id and content_name:
                drama_records.append({
                    "content_id": str(content_id),
                    "name": str(content_name),
                    "cover_url": str(cover_url) if cover_url else "",
                    "tags": tags,
                })
    
    print(f"\nDrama records found: {len(drama_records)}")
    for dr in drama_records[:5]:
        print(f"\n  ID: {dr['content_id']}")
        print(f"  Name: {dr['name']}")
        print(f"  Cover: {dr['cover_url'][:80]}")
        print(f"  Tags: {dr['tags']}")

# 验证可能的 URL 格式
print("\n=== 验证 Drama URL 格式 ===")
if drama_records:
    cid = drama_records[0]['content_id']
    name = drama_records[0]['name']
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=10) as c:
        for path in [
            f"/series/{cid}/",
            f"/drama/{cid}/",
            f"/watch/{cid}/",
            f"/series/{cid}/{slug}/",
            f"/drama/{cid}/{slug}/",
            f"/content/{cid}/",
        ]:
            r2 = c.get(BASE + path)
            print(f"  {r2.status_code} {BASE+path}")
