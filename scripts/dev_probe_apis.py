"""
探测各平台 API 端点。
运行: python scripts/dev_probe_apis.py
"""
import re
import sys
import json
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

PLATFORMS = {
    "reelshort":  "https://www.reelshort.com",
    "flextv":     "https://www.flextv.cc",
    "serealplus": "https://www.sereal.plus",
    "netshort":   "https://netshort.com",
    "melolo":     "https://melolo.com",
    "goodshort":  "https://www.goodshort.com",
    "moboreels":  "https://www.moboreels.com",
}

API_KEYWORDS = [
    "/api/", "/h5/", "/web/", "/rank", "/home", "/drama",
    "/series", "/short", "baseURL", "BASE_URL", "apiUrl",
    "endpoint", "/v1/", "/v2/", "/app/", "/cms/", "Ranklist",
]

def fetch(url: str, timeout=20) -> str:
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, follow_redirects=True, timeout=timeout)
        print(f"  GET {url} -> {r.status_code} ({len(r.text)} chars)")
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  GET {url} -> ERROR: {e}")
        return ""


def find_js_bundles(html: str, base_url: str) -> list[str]:
    urls = []
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', html):
        src = m.group(1)
        if src.startswith("http"):
            urls.append(src)
        elif src.startswith("/"):
            urls.append(base_url.rstrip("/") + src)
    return urls


def scan_js_for_apis(js: str) -> list[str]:
    hits = set()
    # 找字符串形式的路径
    for m in re.finditer(r'["\`]([/][A-Za-z0-9_\-/]+)["\`]', js):
        path = m.group(1)
        if any(k in path for k in API_KEYWORDS):
            hits.add(path)
    # 找 baseURL / apiUrl / BASE_URL 赋值
    for m in re.finditer(r'(?:baseURL|apiUrl|BASE_URL|base_url)\s*[:=]\s*["\`]([^"\`]{5,80})["\`]', js):
        hits.add("BASE: " + m.group(1))
    return sorted(hits)


def probe_platform(key: str, base_url: str):
    print(f"\n{'='*60}")
    print(f"[{key}] {base_url}")
    print(f"{'='*60}")

    html = fetch(base_url)
    if not html:
        print("  !! 无法访问首页，可能需要代理")
        return

    # 提取内联 script 里的 API 端点
    inline_hits: set[str] = set()
    for m in re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL):
        content = m.group(1)
        for h in scan_js_for_apis(content):
            inline_hits.add(h)
    if inline_hits:
        print("  [inline script 端点]")
        for h in sorted(inline_hits)[:30]:
            print("    ", h)

    # 获取 JS bundle
    js_urls = find_js_bundles(html, base_url)
    print(f"  JS bundles 发现 {len(js_urls)} 个")

    # 按大小优先抓最大的几个（通常主 bundle 最大，API 端点最多）
    # 但先只抓前 10 个，避免耗时太长
    all_api_hits: set[str] = set()
    for js_url in js_urls[:15]:
        js = fetch(js_url, timeout=15)
        if not js:
            continue
        hits = scan_js_for_apis(js)
        for h in hits:
            all_api_hits.add(h)

    if all_api_hits:
        print(f"  [JS bundle 端点 共{len(all_api_hits)}条]")
        for h in sorted(all_api_hits)[:50]:
            print("    ", h)
    else:
        print("  [JS bundle 端点] 未找到")

    # 探测常见 API pattern
    print("  [探测常见 API 路径]")
    common_probes = [
        f"{base_url}/api/home",
        f"{base_url}/api/rank",
        f"{base_url}/api/ranking",
        f"{base_url}/api/drama/hot",
        f"{base_url}/api/dramas",
        f"{base_url}/api/series",
        f"{base_url}/api/shorts",
    ]
    for probe_url in common_probes:
        try:
            r = httpx.get(
                probe_url,
                headers={"User-Agent": UA, "Accept": "application/json"},
                follow_redirects=True,
                timeout=8,
            )
            ct = r.headers.get("content-type", "")
            snippet = r.text[:200].replace("\n", " ")
            print(f"    {probe_url} -> {r.status_code} [{ct[:30]}] {snippet[:100]}")
        except Exception as e:
            print(f"    {probe_url} -> {e}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    for key, url in PLATFORMS.items():
        if target and key != target:
            continue
        probe_platform(key, url)
    print("\n完成.")
