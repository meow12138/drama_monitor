"""深度探测 NetShort 和 Melolo API"""
import re
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# ===== NetShort: 扫描最大的 JS bundle =====
print("="*60)
print("NetShort API discovery")
print("="*60)

# 从 9605 bundle 扫描
js_ns = httpx.get("https://netshort.com/_next/static/chunks/9605-ae018d81fefc7055.js",
                  headers={"User-Agent": UA}, timeout=30).text
print(f"9605 bundle size: {len(js_ns)}")

# 所有 API 路径
paths_ns = re.findall(r'["\`](/(?:web|api|h5|v1|v2)[^"\`\n]{1,80})["\`]', js_ns)
print("API paths:")
for p in sorted(set(paths_ns))[:40]:
    print(" ", p)

# 所有域名
domains_ns = re.findall(r'https?://[a-zA-Z0-9.\-]+(?:/[a-zA-Z0-9_\-/]{0,50})?', js_ns)
print("\nDomains:")
for d in sorted(set(d for d in domains_ns if 'netshort' in d.lower() or 'maiya' in d.lower() or 'api' in d.lower()))[:20]:
    print(" ", d)

# 也扫描 1255 bundle
js_ns2 = httpx.get("https://netshort.com/_next/static/chunks/1255-8befde0980f5cba9.js",
                   headers={"User-Agent": UA}, timeout=30).text
print(f"\n1255 bundle size: {len(js_ns2)}")
paths_ns2 = re.findall(r'["\`](/(?:web|api|h5|v1|v2)[^"\`\n]{1,80})["\`]', js_ns2)
print("API paths from 1255:")
for p in sorted(set(paths_ns2))[:40]:
    print(" ", p)
domains_ns2 = re.findall(r'https?://[a-zA-Z0-9.\-]+(?:/[a-zA-Z0-9_\-/]{0,50})?', js_ns2)
api_doms = [d for d in set(domains_ns2) if any(k in d.lower() for k in ['api', 'cdn', 'short', 'drama', 'netshort', 'maiya'])]
print("API-like domains from 1255:")
for d in sorted(api_doms)[:20]:
    print(" ", d)

# ===== Melolo: Next.js data probe =====
print("\n" + "="*60)
print("Melolo API discovery")
print("="*60)

# Get build ID from HTML
html_m = httpx.get("https://melolo.com", headers={"User-Agent": UA}, follow_redirects=True, timeout=20).text
build_id_m = None
m_bid = re.search(r'/_next/static/([a-f0-9A-F_\-]+)/_buildManifest\.js', html_m)
if m_bid:
    build_id_m = m_bid.group(1)
    print(f"Build ID: {build_id_m}")

# Try _next/data
if build_id_m:
    r_nd = httpx.get(f"https://melolo.com/_next/data/{build_id_m}/index.json",
                     headers={"User-Agent": UA}, follow_redirects=True, timeout=15)
    print(f"_next/data: {r_nd.status_code}")
    if r_nd.status_code == 200:
        try:
            d = r_nd.json()
            print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
        except:
            print(r_nd.text[:500])

# 扫描 Next.js data 嵌入
m_ndata = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_m, re.DOTALL)
if m_ndata:
    nd = json.loads(m_ndata.group(1))
    print("\n__NEXT_DATA__ keys:", list(nd.keys()))
    pp = nd.get("props", {}).get("pageProps", {})
    print("pageProps keys:", list(pp.keys()))
    # Show any drama-related data
    for k, v in pp.items():
        if isinstance(v, (list, dict)):
            print(f"\n  {k}:", json.dumps(v, ensure_ascii=False, indent=2)[:2000])

# Scan JS bundles for API paths
print("\n=== Scanning Melolo JS bundles ===")
for js_url in [
    "https://melolo.com/_next/static/chunks/045c83caa4d15373.js",
    "https://melolo.com/_next/static/chunks/647818e2653990e2.js",
]:
    try:
        js_m = httpx.get(js_url, headers={"User-Agent": UA}, timeout=30).text
        print(f"\n{js_url}: size={len(js_m)}")
        paths_m = re.findall(r'["\`](/(?:api|web|v1|v2|dramas?|series|rank)[^"\`\n]{1,80})["\`]', js_m)
        for p in sorted(set(paths_m))[:30]:
            print(" ", p)
        base_urls_m = re.findall(r'(?:baseURL|apiUrl|base_url|serverUrl|API_BASE)\s*[:=]\s*["\`]([^"\`]{8,100})["\`]', js_m)
        for b in base_urls_m[:10]:
            print("  BASE:", b)
        domains_m = re.findall(r'https?://[a-zA-Z0-9.\-]+', js_m)
        api_doms_m = [d for d in set(domains_m) if any(k in d.lower() for k in ['api', 'melolo', 'drama'])]
        for d in sorted(api_doms_m)[:10]:
            print("  DOMAIN:", d)
    except Exception as e:
        print(f"Error: {e}")
