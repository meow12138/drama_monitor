"""验证修正后的 URL 格式"""
import re
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def test(platform, url):
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=10) as c:
        r = c.get(url)
    mark = "OK" if r.status_code == 200 else "XX"
    print(f"  {mark} [{platform}] {r.status_code}  {url[:90]}")

# GoodShort: /drama/ 替代 /dramas/
test("goodshort", "https://www.goodshort.com/drama/a-mistaken-surrogate-for-the-ruthless-billionaire-31000881454")

# ReelShort: 新格式 episode-1-{slug}-{_id}-{chapter_id}
# 从 API 取一条
with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=15) as c:
    r = c.get("https://www.reelshort.com/api/video/book/getTagBook", params={"language": "en", "page": 1, "page_size": 3})
    books = (r.json().get("data") or {}).get("books") or []
    for b in books[:3]:
        _id = b.get("_id", "")
        chapter_id = b.get("chapter_id", "")
        title = b.get("book_title", "")
        serial_num = b.get("serial_number", 1)
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")[:60]
        url_old = f"https://www.reelshort.com/episodes/episode-{serial_num}-{slug}-{chapter_id}"
        url_new = f"https://www.reelshort.com/episodes/episode-{serial_num}-{slug}-{_id}-{chapter_id}"
        r2 = c.get(url_old, timeout=8)
        r3 = c.get(url_new, timeout=8)
        print(f"  title={title[:30]}")
        print(f"    OLD {r2.status_code}: ...{url_old[-50:]}")
        print(f"    NEW {r3.status_code}: ...{url_new[-60:]}")

# MoboReels: /dramas/ 替代 /series/
test("moboreels", "https://www.moboreels.com/dramas/41896322")
