"""检查爬虫请求 Sereal+ 拿到的页面与直接 httpx 请求是否一致"""
import asyncio, json
from app.scrapers.serealplus import SerealPlusScraper, _deref
from bs4 import BeautifulSoup

async def test():
    async with SerealPlusScraper() as s:
        html = await s.fetch_html(s.base_url)
    
    print(f"html len from scraper: {len(html)}")
    soup = BeautifulSoup(html, 'html.parser')
    scripts = [sc for sc in soup.find_all('script', src=False) if len(sc.get_text()) > 5000]
    print(f"Large scripts: {len(scripts)}, sizes={[len(sc.get_text()) for sc in scripts]}")
    
    if not scripts:
        print("No large scripts! Different page returned.")
        # Check for inline script content
        all_scripts = soup.find_all('script', src=False)
        print(f"Total inline scripts: {len(all_scripts)}")
        for i, s in enumerate(all_scripts):
            print(f"  Script {i}: len={len(s.get_text())}, starts={s.get_text()[:50]}")
        return
    
    nuxt_script = max(scripts, key=lambda sc: len(sc.get_text()))
    content = nuxt_script.get_text().strip()
    print(f"Nuxt script len={len(content)}, starts={content[:80]}")
    
    try:
        arr = json.loads(content)
        print(f"Array len={len(arr)}")
        
        # Find drama dicts
        drama_dicts = [(i, el) for i, el in enumerate(arr) if isinstance(el, dict) and "contentId" in el and "contentName" in el]
        print(f"Drama dicts: {len(drama_dicts)}")
        
        # Find column dicts
        col_dicts = [(i, el) for i, el in enumerate(arr) if isinstance(el, dict) and "columnName" in el and "records" in el]
        print(f"Column dicts: {len(col_dicts)}")
        for i, el in col_dicts:
            col_name = _deref(arr, el.get("columnName"))
            records = _deref(arr, el.get("records"))
            print(f"  [{i}] name={col_name}, records_type={type(records).__name__}, records_len={len(records) if isinstance(records, list) else 'N/A'}")
    except Exception as e:
        print(f"JSON parse error: {e}")
        print(content[:200])

asyncio.run(test())
