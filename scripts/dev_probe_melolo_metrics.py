"""探索 Melolo 是否有点赞/播放/收藏数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://melolo.com"

# 1. 先从首页拿一个真实的剧集链接
print("=== 步骤1: 从首页取剧集链接 ===")
r = httpx.get(BASE, headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
soup = BeautifulSoup(r.text, "html.parser")
drama_links = list(set(
    a.get("href") for a in soup.find_all("a", href=re.compile(r"/dramas/"))
    if a.get("href")
))
print(f"首页 /dramas/ 链接: {drama_links[:5]}")

# 2. 抓取一个剧集详情页
if drama_links:
    detail_url = drama_links[0] if drama_links[0].startswith("http") else BASE + drama_links[0]
else:
    detail_url = "https://melolo.com/dramas/fated-to-find-you"

print(f"\n=== 步骤2: 抓取详情页 {detail_url} ===")
r2 = httpx.get(detail_url, headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
print(f"Status: {r2.status_code}, size: {len(r2.text)}")
html = r2.text
soup2 = BeautifulSoup(html, "html.parser")

# 3. 找 K/M 数字
print("\n=== K/M 格式数字元素 ===")
knum_re = re.compile(r"\d+\.?\d*[KkMm]")
for el in soup2.find_all(string=knum_re)[:10]:
    parent = el.parent
    print(f"  '{el.strip()[:30]}' | {parent.name}.{parent.get('class', [])}")

# 4. 找 __NEXT_DATA__
print("\n=== __NEXT_DATA__ ===")
nd_m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
if nd_m:
    nd = json.loads(nd_m.group(1))
    pp = nd.get("props", {}).get("pageProps", {})
    print(f"pageProps keys: {list(pp.keys())}")
    
    def find_metrics(obj, path="", depth=0):
        if depth > 6:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = k.lower()
                if any(kw in kl for kw in ["play", "like", "collect", "watch", "view", "fan", "follow", "count", "num", "total"]):
                    if isinstance(v, (int, float)) and v > 0:
                        print(f"  {path}.{k} = {v:,}")
                    elif isinstance(v, str) and re.match(r"^\d+$", str(v)) and int(v) > 0:
                        print(f"  {path}.{k} = {int(v):,}")
                find_metrics(v, f"{path}.{k}", depth + 1)
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:3]):
                find_metrics(v, f"{path}[{i}]", depth + 1)
    
    find_metrics(pp)
else:
    print("No __NEXT_DATA__")

# 5. 找内嵌 JSON 里的大数字
print("\n=== JSON 大数值字段（> 100）===")
json_nums = re.findall(r'"(\w+)"\s*:\s*(\d{3,})', html)
metrics_kws = ["play", "like", "collect", "watch", "view", "fan", "follow", "count", "num", "total"]
for k, v in json_nums:
    if any(kw in k.lower() for kw in metrics_kws):
        print(f"  {k}: {int(v):,}")

# 6. 看页面上有哪些互动按钮/数字
print("\n=== 页面互动元素 ===")
for btn in soup2.find_all(["button", "span", "div"], class_=re.compile(r"like|collect|follow|watch|play|count", re.I)):
    text = btn.get_text(strip=True)[:40]
    if text:
        print(f"  {btn.name}.{btn.get('class', [])} -> '{text}'")

# 7. 找 API 调用相关的 URL
print("\n=== 页面内 API 相关字符串 ===")
api_patterns = re.findall(r'["\`](/api/[^"\`\s]{3,80})["\`]', html)
for p in sorted(set(api_patterns))[:20]:
    print(f"  {p}")
