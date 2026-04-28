"""精确诊断 _parse_nuxt_array 内部状态"""
import asyncio, json
from app.scrapers.serealplus import SerealPlusScraper, _deref
from bs4 import BeautifulSoup

async def test():
    async with SerealPlusScraper() as s:
        html = await s.fetch_html(s.base_url)

    soup = BeautifulSoup(html, 'html.parser')
    scripts = [sc for sc in soup.find_all('script', src=False) if len(sc.get_text()) > 5000]
    nuxt_script = max(scripts, key=lambda sc: len(sc.get_text()))
    arr = json.loads(nuxt_script.get_text().strip())

    # 第一遍：收集 drama_by_idx
    drama_by_idx = {}
    for i, el in enumerate(arr):
        if isinstance(el, dict) and "contentId" in el and "contentName" in el:
            cid = _deref(arr, el.get("contentId"))
            cname = _deref(arr, el.get("contentName"))
            if cid and cname:
                drama_by_idx[i] = {"content_id": str(cid), "drama_name": str(cname)}

    print(f"drama_by_idx keys: {sorted(drama_by_idx.keys())}")

    # 第二遍：找栏目
    for i, el in enumerate(arr):
        if not isinstance(el, dict) or "columnName" not in el or "records" not in el:
            continue
        col_name = _deref(arr, el.get("columnName"))
        if not isinstance(col_name, str) or "banner" in col_name.lower():
            continue
        records_ref = _deref(arr, el.get("records"))
        if not isinstance(records_ref, list):
            continue

        print(f"\nColumn [{i}] '{col_name}' records={records_ref}")
        for ref in records_ref:
            idx = ref if isinstance(ref, int) else None
            drama = drama_by_idx.get(idx) if idx is not None else None
            print(f"  ref={ref}, in_drama_by_idx={idx in drama_by_idx if idx else False}, drama={drama['drama_name'][:30] if drama else 'NOT FOUND'}")

asyncio.run(test())
