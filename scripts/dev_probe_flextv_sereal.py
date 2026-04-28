"""探测 FlexTV 嵌入数据 + Sereal+ API headers"""
import re
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# ===== FlexTV =====
print("="*60)
print("FlexTV")
print("="*60)
html = httpx.get("https://www.flextv.cc", headers={"User-Agent": UA}, follow_redirects=True, timeout=30).text
print(f"HTML size: {len(html)}")

# 找 __NUXT__ 或 __PAYLOAD__
m = re.search(r'window\.__NUXT__=(.*?)</script>', html, re.DOTALL)
if m:
    print("Found __NUXT__, len:", len(m.group(1)))
    print(m.group(1)[:3000])

# 找 domain/api
domains = re.findall(r'https?://[a-zA-Z0-9.\-]+(?:/[a-zA-Z0-9_\-/.?=&]{0,80})?', html)
api_doms = [d for d in set(domains) if any(k in d for k in ['api', 'cdn', 'static', 'gateway', 'service', 'short', 'drama'])]
print("\nAPI-like domains in HTML:")
for d in sorted(api_doms)[:20]:
    print(" ", d)

# 找有意思的字符串
api_strings = re.findall(r'["\']([^"\']{5,100}(?:api|endpoint|baseurl|gateway)[^"\']{0,100})["\']', html, re.IGNORECASE)
print("\nAPI strings in HTML:")
for s in list(set(api_strings))[:20]:
    print(" ", s)

# 找所有 src 为外部域名的 script
external_scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
print("\nExternal scripts:")
for s in external_scripts:
    print(" ", s)

# ===== Sereal+ =====
print("\n" + "="*60)
print("Sereal+ with proper headers")
print("="*60)

API_BASE = "https://web-api.serealplus.com"
WEB_BASE = "https://www.sereal.plus"

# 尝试找 Sereal+ 的其他 JS bundles
html2 = httpx.get(WEB_BASE, headers={"User-Agent": UA}, follow_redirects=True, timeout=20).text
scripts = re.findall(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', html2)
print(f"Sereal+ scripts found: {len(scripts)}")
for s in scripts[:10]:
    print(" ", s)

# 扫描 HTML 里的内联 API 调用
inline_apis = re.findall(r'["\`]([^"\`]*(?:api|drama|rank)[^"\`]{3,60})["\`]', html2, re.IGNORECASE)
print("\nInline API strings:")
for s in sorted(set(inline_apis))[:30]:
    print(" ", s)

# 尝试 Sereal+ API with channel/platform headers
SEREAL_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": WEB_BASE + "/",
    "Origin": WEB_BASE,
    "channel": "h5",
    "platform": "web",
    "Content-Type": "application/json",
}

# 扫描 bundle 里的路径
for script_url in scripts[:5]:
    if not script_url.startswith("http"):
        script_url = WEB_BASE + script_url
    try:
        js_r = httpx.get(script_url, headers={"User-Agent": UA}, timeout=20)
        js = js_r.text
        print(f"\nScript {script_url}: size={len(js)}")
        paths = sorted(set(re.findall(r'"(/[A-Za-z0-9_\-/]{3,80})"', js)))
        api_paths = [p for p in paths if any(k in p for k in ['/drama', '/rank', '/home', '/video', '/api', '/series'])]
        for p in api_paths[:30]:
            print(" ", p)
        base_urls = re.findall(r'(?:baseURL|apiBase|base_url|serverUrl)\s*[:=]\s*["\`]([^"\`]{8,100})["\`]', js)
        for b in base_urls[:5]:
            print("  BASE:", b)
    except Exception as e:
        print(f"Error fetching {script_url}: {e}")
