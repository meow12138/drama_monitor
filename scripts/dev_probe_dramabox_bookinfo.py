"""查看 DramaBox bookInfo 完整字段"""
import re, json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as c:
    c.get("https://www.dramabox.com")
    r = c.get("https://www.dramabox.com/drama/41000121776/Watch-Out-Im-The-Lady-Boss")

nd_m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
nd = json.loads(nd_m.group(1))
book_info = nd["props"]["pageProps"]["bookInfo"]

print("=== bookInfo 完整字段 ===")
for k, v in book_info.items():
    if not isinstance(v, (dict, list)):
        print(f"  {k}: {v}")
    else:
        print(f"  {k}: [{type(v).__name__}]")

print("\n=== 数值字段 ===")
for k, v in book_info.items():
    if isinstance(v, (int, float)) and v > 0:
        print(f"  {k} = {v:,}")
    elif isinstance(v, str) and re.match(r'^\d+$', v) and int(v) > 0:
        print(f"  {k} = {int(v):,}")
