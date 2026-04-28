"""分析 FlexTV NUXT_DATA 数组找标签字段"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.flextv.cc"

ep_url = "/en/episodes/episode-1-justice-in-blood-dubbed-mEZqoBAz8Q"
r = httpx.get(BASE + ep_url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
              follow_redirects=True, timeout=20)
html = r.text
soup = BeautifulSoup(html, "html.parser")

# 分析 NUXT_DATA 数组
nd = soup.find("script", {"id": "__NUXT_DATA__"})
arr = json.loads(nd.get_text())
print(f"Array length: {len(arr)}")

# 过滤出所有短字符串（可能的标签/题材）
TAG_BLACKLIST = {"en", "en-US", "ltr", "rtl", "utf-8", "true", "false", "null",
                 "completed", "ongoing", "complete", "", "N/A", "default", "auto"}
short_str_indices = []
for i, v in enumerate(arr):
    if not isinstance(v, str):
        continue
    v = v.strip()
    if len(v) < 2 or len(v) > 40:
        continue
    if v.lower() in TAG_BLACKLIST:
        continue
    if v.startswith("http") or v.startswith("/") or v.startswith("{") or v.startswith("["):
        continue
    if re.search(r'[<>{}=|]', v):
        continue
    short_str_indices.append((i, v))

print(f"\nPotential tag strings ({len(short_str_indices)}):")
for i, v in short_str_indices[:80]:
    print(f"  [{i}] {repr(v)}")

# 查找特定已知标签
known_tags = ["Heiress", "Female-Centric", "Rich Family", "Family", "Romance",
              "CEO", "Contract-Couple", "Contemporary", "Sweet Romance", "Rebirth"]
print("\nSearching for known tags:")
for tag in known_tags:
    if tag in arr:
        print(f"  FOUND: {repr(tag)} at index {arr.index(tag)}")
    else:
        # 大小写不敏感搜索
        for i, v in enumerate(arr):
            if isinstance(v, str) and v.strip().lower() == tag.lower():
                print(f"  FOUND (case-insensitive): {repr(v)} at index {i}")
                break

# 检查数组中的整数序列（可能是剧的数据结构）
print("\n\nIntegers and their neighbors:")
for i, v in enumerate(arr):
    if isinstance(v, int) and 1000 <= v <= 100000000:
        prev = arr[i-1] if i > 0 else None
        next_ = arr[i+1] if i < len(arr)-1 else None
        print(f"  [{i}] {v} | prev={repr(prev)[:30]} | next={repr(next_)[:30]}")

# 打印数组的前200个元素看结构
print("\n\nFirst 200 elements of NUXT_DATA array:")
for i, v in enumerate(arr[:200]):
    if v is not None and v != 0 and v != "" and v is not False:
        print(f"  [{i}] {type(v).__name__}: {repr(v)[:80]}")
