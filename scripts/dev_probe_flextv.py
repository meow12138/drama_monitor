"""深入探测 FlexTV 的 Nuxt bundle"""
import re
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# FlexTV Nuxt bundle
js = httpx.get("https://www.flextv.cc/_nuxt/BkrJISLG.js", headers={"User-Agent": UA}, timeout=30).text
print(f"JS size: {len(js)} chars")

# 扫描 API 路径
paths = re.findall(r'"(/[A-Za-z0-9_\-/]{3,60})"', js)
# 扫描 base URL
base_urls = re.findall(r'(?:baseURL|apiBase|base_url|serverUrl|apiUrl|baseUrl)\s*[:=]\s*["\`]([^"\`]{8,80})["\`]', js)
domains = re.findall(r'https?://[a-zA-Z0-9.\-]+(?:/[a-zA-Z0-9_\-/]{3,60})?', js)

print("\n=== Base URLs ===")
for u in sorted(set(base_urls))[:20]:
    print(" ", u)

print("\n=== All domains found ===")
for d in sorted(set(domains))[:30]:
    print(" ", d)

print("\n=== API paths (interesting) ===")
API_KEYWORDS = ["/api/", "/h5/", "/web/", "/rank", "/home", "/drama", "/series", "/short", "/list", "/cms", "/app", "/v1", "/v2"]
interesting = sorted(set(p for p in paths if any(k in p for k in API_KEYWORDS)))
for p in interesting[:60]:
    print(" ", p)

print("\n=== All paths ===")
all_paths = sorted(set(p for p in paths if len(p) > 5))
for p in all_paths[:100]:
    print(" ", p)
