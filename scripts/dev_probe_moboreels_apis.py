"""扫描 MoboReels 各 chunk 里的 API 路径"""
import re

import httpx

client = httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=30)
chunks = ["73af351.js", "b0a37ad.js", "6b6b5c6.js", "37fab0b.js"]

for fname in chunks:
    js = client.get(f"https://www.moboreels.com/_nuxt/{fname}").text
    paths = sorted(set(re.findall(r"\"(/[A-Za-z0-9/_\-]+)\"", js)))
    interesting = [
        p
        for p in paths
        if any(k in p for k in ["/api/", "/h5/", "/web/api", "/series", "Ranklist", "/home", "/rank"])
    ]
    base_urls = re.findall(r"baseURL[^,;]{0,80}", js)
    print(f"--- {fname} (size={len(js)}) ---")
    for p in interesting[:40]:
        print("  api:", p)
    for b in base_urls[:5]:
        print("  base:", b)
