"""调试 FlexTV span.num 和 NUXT_DATA tag 提取"""
import re
import json
import httpx
from bs4 import BeautifulSoup
from app.scrapers.flextv import FlexTVScraper, _IS_KNUM_RE, _parse_knum

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BASE = "https://www.flextv.cc"

test_urls = [
    "/en/episodes/episode-1-justice-in-blood-dubbed-mEZqoBAz8Q",
    "/en/episodes/episode-1-choosing-the-devil-over-you-r0OB5MkZXA",
    "/en/episodes/episode-1-the-tiny-tyrant-of-go-dubbed-WKzLolDOr0",
]

for url in test_urls:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    r = httpx.get(BASE + url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    }, follow_redirects=True, timeout=20)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. 所有 span.num 值
    all_nums = [(el.get_text(strip=True), el.find_parent().get("class", []) if el.find_parent() else [])
                for el in soup.select("span.num")]
    print(f"\nAll span.num values ({len(all_nums)}):")
    for text, parent_cls in all_nums[:15]:
        is_knum = bool(_IS_KNUM_RE.match(text))
        print(f"  {repr(text)} (knum={is_knum}) parent_class={parent_cls}")
    
    # 2. 数值列表
    valid = [_parse_knum(t) for t, _ in all_nums if _IS_KNUM_RE.match(t)]
    print(f"\nValid nums: {valid[:10]}")
    print(f"like_count={valid[0] if valid else 0}, collect_count={valid[1] if len(valid)>1 else 0}")
    
    # 3. NUXT_DATA tag 调试
    nd = soup.find("script", {"id": "__NUXT_DATA__"})
    if nd:
        arr = json.loads(nd.get_text())
        print(f"\nNUXT array len={len(arr)}")
        
        # 找含 'tag' 和 'detail' 键的 dict
        state_dicts = [(i, el) for i, el in enumerate(arr)
                       if isinstance(el, dict) and 'tag' in el and 'detail' in el]
        print(f"State dicts with 'tag'+'detail': {[(i, el) for i, el in state_dicts]}")
        
        for i, sd in state_dicts:
            tag_ref = sd.get('tag')
            print(f"\n  State[{i}].tag_ref = {tag_ref}")
            if isinstance(tag_ref, int) and tag_ref < len(arr):
                tag_list = arr[tag_ref]
                print(f"  arr[{tag_ref}] = {repr(tag_list)[:100]}")
                if isinstance(tag_list, list):
                    for ti in tag_list[:5]:
                        if isinstance(ti, int) and ti < len(arr):
                            tobj = arr[ti]
                            print(f"    arr[{ti}] = {repr(tobj)[:100]}")
                            if isinstance(tobj, dict):
                                name_ref = tobj.get('name')
                                if isinstance(name_ref, int) and name_ref < len(arr):
                                    print(f"      arr[{name_ref}] = {repr(arr[name_ref])}")
        
        # 也找第二个标签
        for i, el in enumerate(arr):
            if isinstance(el, dict) and 'tag' in el and len(el) == 1:
                print(f"\n  Dict with only 'tag' key: arr[{i}] = {el}")
