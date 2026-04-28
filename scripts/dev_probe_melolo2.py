"""深度解析 Melolo RSC 流数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://melolo.com"

# 抓详情页
r = httpx.get(f"{BASE}/dramas/fated-to-find-you", headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
html = r.text
print(f"Status: {r.status_code}, size: {len(html)}")

# 1. 解析所有 self.__next_f.push 的数据
pushes = re.findall(r'self\.__next_f\.push\(\[(.*?)\]\)', html, re.DOTALL)
print(f"\nRSC push blocks: {len(pushes)}")

# 合并所有 JSON 字符串块
all_json_strs = []
for push in pushes:
    # 格式: [chunk_id, "json_string"] 或 [1, "..."]
    m = re.match(r'(\d+),(.+)', push.strip(), re.DOTALL)
    if m:
        chunk_id, content = m.group(1), m.group(2).strip()
        if content.startswith('"') and content.endswith('"'):
            try:
                # 内容是 JSON 字符串，先 unescape
                inner = json.loads(content)
                all_json_strs.append(inner)
            except:
                pass

print(f"Decoded RSC strings: {len(all_json_strs)}")

# 2. 在合并内容里找互动数字
combined = "\n".join(all_json_strs)
print(f"Combined RSC content length: {len(combined)}")

# 找互动相关字段
metrics_kws = ["play", "like", "collect", "watch", "view", "fan", "follow",
               "count", "num", "total", "episode", "rating", "score", "vote"]
found = {}
for kw in metrics_kws:
    matches = re.findall(rf'"({kw}[A-Za-z_]*)"\s*:\s*(\d+)', combined, re.IGNORECASE)
    for k, v in matches:
        if int(v) > 0:
            found[k] = int(v)

print("\n=== 互动数值字段 ===")
for k, v in sorted(found.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(f"  {k}: {v:,}")

# 3. 找剧集基本信息
print("\n=== 剧名/剧集信息 ===")
drama_titles = re.findall(r'"(?:title|name|seriesName|dramaName)"\s*:\s*"([^"]{3,60})"', combined)
print(f"  Drama titles: {drama_titles[:5]}")

# 4. 探测公共 API 端点
print("\n=== 探测 Melolo 公共 API ===")
test_apis = [
    f"{BASE}/api/series/fated-to-find-you",
    f"{BASE}/api/dramas/fated-to-find-you",
    f"{BASE}/api/drama/fated-to-find-you",
    f"{BASE}/api/series",
    f"{BASE}/api/top",
    f"{BASE}/api/popular",
    f"{BASE}/api/rankings",
]
with httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"}, follow_redirects=True, timeout=8) as c:
    for api_url in test_apis:
        try:
            resp = c.get(api_url)
            ct = resp.headers.get("content-type", "")
            if "json" in ct or resp.status_code != 404:
                print(f"  [{resp.status_code}] {api_url}: {resp.text[:100]}")
        except Exception as e:
            print(f"  ERR {api_url}: {e}")

# 5. 从 HTML 找页面上可见的任何数字
print("\n=== HTML 页面可见数字元素 ===")
soup = BeautifulSoup(html, "html.parser")
for el in soup.find_all(["span", "div", "p"], string=re.compile(r"^\s*\d[\d,\.]*[KkMm]?\s*$")):
    parent_cls = el.find_parent(class_=True)
    print(f"  '{el.get_text(strip=True)}' | class: {el.get('class')} | parent: {parent_cls.get('class') if parent_cls else None}")
