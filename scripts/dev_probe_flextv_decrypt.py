"""解密 FlexTV API 数据 + 验证点赞/收藏/标签提取"""
import re
import json
import httpx
from base64 import b64decode
from bs4 import BeautifulSoup

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.flextv.cc"

def parse_knum(text: str) -> int:
    """解析 '17.7K' '23.3K' '1.2M' 等为整数"""
    t = text.strip().upper()
    try:
        if t.endswith("K"):
            return int(float(t[:-1]) * 1000)
        if t.endswith("M"):
            return int(float(t[:-1]) * 1_000_000)
        return int(float(t))
    except:
        return 0

def try_decrypt(b64_data: str, key: bytes, iv: bytes = None) -> dict | None:
    if not HAS_CRYPTO:
        return None
    try:
        ct = b64decode(b64_data.strip())
        iv2 = iv or key[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv=iv2)
        plain = unpad(cipher.decrypt(ct), AES.block_size)
        return json.loads(plain.decode("utf-8"))
    except:
        return None

# 候选 AES 密钥（均来自 FlexTV JS bundle 扫描）
CANDIDATE_KEYS = [
    b"3zxNedKJCoLV4Fi7",
    b"52u3itng7y4omkja",
    b"859mw3lnt40rxbca",
    b"FifZlSY4nb0eg6k8oDG2xC3UIMOwdBru",
]

# 获取详情页
ep_url = "/en/episodes/episode-1-justice-in-blood-dubbed-mEZqoBAz8Q"
r = httpx.get(BASE + ep_url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
              follow_redirects=True, timeout=20)
html = r.text
soup = BeautifulSoup(html, "html.parser")

print(f"Status: {r.status_code}, size: {len(html)}")

# 1. 提取点赞数、收藏数
print("\n=== 点赞 / 收藏 / 评分 ===")
icon_wrappers = soup.select("div.icon-wrapper")
for wrapper in icon_wrappers:
    num_el = wrapper.select_one("span.num")
    if num_el:
        classes = wrapper.get("class", [])
        num_text = num_el.get_text(strip=True)
        is_collect = "icon-collect-wrapper" in classes
        kind = "collect(收藏)" if is_collect else "like(点赞)"
        print(f"  {kind}: {num_text} → {parse_knum(num_text)}")

# 另一种方法：找所有 K/M 数字
knum_els = soup.find_all("span", class_="num")
print(f"\n  All span.num: {[el.get_text(strip=True) for el in knum_els]}")

# 2. 解析 NUXT_DATA，尝试解密
print("\n=== NUXT_DATA API 解密尝试 ===")
nd = soup.find("script", {"id": "__NUXT_DATA__"})
if nd:
    arr = json.loads(nd.get_text())
    data_map = arr[2] if isinstance(arr[2], dict) else {}
    
    for api_key, val_idx in data_map.items():
        if not isinstance(val_idx, int) or val_idx >= len(arr):
            continue
        raw = arr[val_idx]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except:
                continue
        if not isinstance(raw, dict) or raw.get("code") != 0:
            continue
        
        enc_data = raw.get("data", "")
        if not isinstance(enc_data, str) or len(enc_data) < 20:
            continue
        
        print(f"\n  Encrypted endpoint: {api_key.split('-')[1] if '-' in api_key else api_key[:60]}")
        print(f"  data len={len(enc_data)}, preview={enc_data[:40]}...")
        
        for key in CANDIDATE_KEYS:
            # 尝试不同 IV
            for iv in [key[:16], b"\x00"*16, None]:
                result = try_decrypt(enc_data, key, iv)
                if result:
                    print(f"  ✓ DECRYPTED with key={key.decode()}, iv={iv}")
                    print(f"  Result preview: {json.dumps(result, ensure_ascii=False)[:500]}")
                    break
            else:
                continue
            break

# 3. 扫描 NUXT_DATA 数组找标签字符串
print("\n=== NUXT_DATA 数组扫描标签 ===")
if nd:
    arr2 = json.loads(nd.get_text())
    # 找短字符串（可能是标签）
    short_strs = [v for v in arr2 if isinstance(v, str) and 3 <= len(v) <= 30 
                  and v[0].isupper() and " " in v or (v[0].isupper() and "-" in v)]
    print(f"  Short capitalized strings: {short_strs[:30]}")
    
    # 也找纯字符串标签
    all_strs = [v for v in arr2 if isinstance(v, str) and 2 <= len(v) <= 25 
                and not v.startswith("http") and not v.startswith("{") and "/" not in v]
    print(f"\n  All short strings: {all_strs[:50]}")
