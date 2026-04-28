"""探测 FlexTV /web/index API 和 Sereal+ 正确 headers"""
import re
import json
import httpx
from base64 import b64decode

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# ===== FlexTV /web/index =====
print("="*60)
print("FlexTV /web/index API")
print("="*60)

# 先获取首页拿到 session token
r0 = httpx.get("https://www.flextv.cc", headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
# 从 cookie 里拿 session
cookies = dict(r0.cookies)
print("Cookies:", cookies)

# 从 __NUXT_DATA__ 里提取 session id
m = re.search(r'"get-/web/index-undefined-en-([a-z0-9]+)"', r0.text)
session_id = m.group(1) if m else None
print(f"Session ID: {session_id}")

# 提取 encrypted data
m2 = re.search(r'"get-/web/index-undefined-en-[a-z0-9]+":\s*"(\{[^"]+\})"', r0.text)
if not m2:
    # Try escaped JSON string
    m2 = re.search(r'"get-/web/index-undefined-en-[a-z0-9]+":(\{[^}]+\})', r0.text)

# Raw extract
idx = r0.text.find("get-/web/index-undefined-en-")
if idx != -1:
    snippet = r0.text[idx:idx+200]
    print(f"Raw snippet: {snippet}")

# 尝试直接调用 /web/index
FLEX_API = "https://api-quick.flextv.cc"
FLEX_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": "https://www.flextv.cc/",
    "Origin": "https://www.flextv.cc",
    "lang": "en",
}
if session_id:
    FLEX_HEADERS["x-session-id"] = session_id
    FLEX_HEADERS["token"] = session_id

for path in ["/web/index", "/web/home", "/web/drama/list"]:
    try:
        r = httpx.get(FLEX_API + path, headers=FLEX_HEADERS, timeout=10)
        print(f"\nGET {FLEX_API+path} -> {r.status_code}")
        print(r.text[:500])
    except Exception as e:
        print(f"\nGET {FLEX_API+path} -> ERROR: {e}")

# 找 FlexTV bundle 里的 AES 密钥
print("\n=== Searching for AES key in FlexTV bundle ===")
js = httpx.get("https://www.flextv.cc/_nuxt/BkrJISLG.js", headers={"User-Agent": UA}, timeout=30).text
# 找 16/32 字节的字符串（AES key 候选）
key_candidates = re.findall(r'["\`]([a-zA-Z0-9]{16,32})["\`]', js)
# 过滤掉太常见的
key_candidates = [k for k in key_candidates if not all(c.isdigit() for c in k)]
print(f"Possible AES keys ({len(key_candidates)} total):")
for k in sorted(set(key_candidates))[:30]:
    print(f"  '{k}'")

# ===== Sereal+ =====
print("\n" + "="*60)
print("Sereal+ with various headers")
print("="*60)

SEREAL_API = "https://web-api.serealplus.com"

# 获取 Sereal+ cookie
sr_r = httpx.get("https://www.sereal.plus", headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
sr_cookies = dict(sr_r.cookies)
print("Sereal+ cookies:", sr_cookies)

# 找内联 token
m_token = re.search(r'token["\s:=]+["\']([a-zA-Z0-9_.\-]{20,})["\']', sr_r.text)
if m_token:
    print(f"Token: {m_token.group(1)}")

# 尝试不同头部组合
test_paths = [
    "/drama/api/front/drama/recommend/list",
    "/drama/api/front/drama/hot/list",
    "/drama/api/front/rank/list",
    "/api/front/drama/list",
    "/drama/api/front/web/home",
    "/drama/api/front/drama/index",
]

for path in test_paths:
    for headers_combo in [
        {"User-Agent": UA, "Origin": "https://www.sereal.plus", "Referer": "https://www.sereal.plus/"},
        {"User-Agent": UA, "Origin": "https://www.sereal.plus", "channel": "h5", "platform": "web"},
        {"User-Agent": UA, "x-channel": "h5", "x-platform": "web"},
    ]:
        try:
            r = httpx.get(SEREAL_API + path, headers=headers_combo, timeout=8)
            if r.status_code == 200:
                resp_text = r.text[:200]
                if '"code":' in resp_text and '"U0001"' not in resp_text:
                    print(f"\n*** MATCH: {path} -> {r.status_code}")
                    print(resp_text[:500])
                    break
                else:
                    print(f"  {path} -> {r.status_code}: {resp_text[:80]}")
        except Exception as e:
            print(f"  {path} -> ERROR: {e}")
        break  # only try first headers combo per path for speed
