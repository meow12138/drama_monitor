"""调试 Sereal+ Nuxt 解析"""
import asyncio, json
from app.scrapers.serealplus import SerealPlusScraper, _deref
from bs4 import BeautifulSoup

async def test():
    async with SerealPlusScraper() as s:
        html = await s.fetch_html(s.base_url)

    soup = BeautifulSoup(html, 'html.parser')
    scripts = [sc for sc in soup.find_all('script', src=False) if len(sc.get_text()) > 5000]
    print(f"Large scripts: {len(scripts)}, sizes={[len(sc.get_text()) for sc in scripts]}")

    nuxt_script = max(scripts, key=lambda sc: len(sc.get_text()))
    content = nuxt_script.get_text().strip()
    print(f"Biggest script len={len(content)}, starts={content[:80]}")

    arr = json.loads(content)
    print(f"Array len={len(arr)}")

    # 找含 contentId+contentName 的 dict
    drama_dicts = [(i, el) for i, el in enumerate(arr) if isinstance(el, dict) and "contentId" in el and "contentName" in el]
    print(f"Drama dicts: {len(drama_dicts)}")
    if drama_dicts:
        i, el = drama_dicts[0]
        print(f"  Sample dict[{i}]: {el}")
        cid_ref = el.get("contentId")
        cid = _deref(arr, cid_ref)
        cname = _deref(arr, el.get("contentName"))
        url = _deref(arr, el.get("url"))
        print(f"  contentId_ref={cid_ref}, value={cid}")
        print(f"  contentName={cname}")
        print(f"  url={url}")

    # 找含 columnName+records 的 dict
    col_dicts = [(i, el) for i, el in enumerate(arr) if isinstance(el, dict) and "columnName" in el and "records" in el]
    print(f"\nColumn dicts: {len(col_dicts)}")
    for i, el in col_dicts[:5]:
        col_name = _deref(arr, el.get("columnName"))
        records = _deref(arr, el.get("records"))
        print(f"  [{i}] name={col_name}, records={records}")

asyncio.run(test())
