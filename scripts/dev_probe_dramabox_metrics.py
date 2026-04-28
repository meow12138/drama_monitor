"""探测 DramaBox 详情页是否含播放/收藏数据"""
import re
import json
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
url = "https://www.dramabox.com/drama/41000121776/Watch-Out-Im-The-Lady-Boss"

with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as c:
    c.get("https://www.dramabox.com")  # get homepage first for cookies
    r = c.get(url)

print("Status:", r.status_code, "size:", len(r.text))
html = r.text
soup = BeautifulSoup(html, "html.parser")

# 1. 找 K/M 数字
knum_re = re.compile(r"\d+\.?\d*[KkMm]")
knum_els = soup.find_all(string=knum_re)
print("\nK/M 数字元素:")
for el in knum_els[:10]:
    parent = el.parent
    print(f"  '{el.strip()[:30]}' | {parent.name}.{parent.get('class', [])}")

# 2. JSON 里的 play/like/collect 相关数值
for kw in ["playNum", "collectNum", "likeNum", "viewNum", "watchNum", "fansNum", "favoriteNum"]:
    m = re.search(rf'"{kw}"\s*:\s*(\d+)', html)
    if m:
        print(f"  JSON [{kw}]: {m.group(0)}")

# 3. __NEXT_DATA__
nd_m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
if nd_m:
    nd = json.loads(nd_m.group(1))
    print(f"\n__NEXT_DATA__ keys: {list(nd.keys())}")
    pp = nd.get("props", {}).get("pageProps", {})
    print(f"pageProps keys: {list(pp.keys())[:10]}")
    # 递归找数值字段
    def find_nums(obj, path="", depth=0):
        if depth > 6:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(kw in k.lower() for kw in ["play", "like", "collect", "watch", "view", "fan", "favor"]):
                    print(f"  {path}.{k} = {v}")
                find_nums(v, f"{path}.{k}", depth + 1)
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:3]):
                find_nums(v, f"{path}[{i}]", depth + 1)
    find_nums(pp)
else:
    print("\nNo __NEXT_DATA__")
    # 找所有数字 > 1000
    big_nums = re.findall(r'"(\w+)"\s*:\s*(\d{4,})', html)
    print("Numbers > 1000 in JSON:", big_nums[:20])
