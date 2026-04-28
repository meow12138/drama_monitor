"""调试 5 个站点的首页解析"""
import asyncio

import httpx
from bs4 import BeautifulSoup

from app.scrapers.flextv import FlexTVScraper
from app.scrapers.goodshort import GoodShortScraper
from app.scrapers.melolo import MeloloScraper
from app.scrapers.reelshort import ReelShortScraper
from app.scrapers.serealplus import SerealPlusScraper

CASES = [
    (ReelShortScraper, "https://www.reelshort.com"),
    (SerealPlusScraper, "https://www.sereal.plus"),
    (FlexTVScraper, "https://www.flextv.cc"),
    (GoodShortScraper, "https://www.goodshort.com"),
    (MeloloScraper, "https://melolo.com"),
]


def dump(scraper_cls, url):
    scraper = scraper_cls()
    html = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    print(f"=== {scraper.platform_key} ({url}) ===")
    for label, titles in (("hot", scraper.HOT_SECTION_TITLES), ("rising", scraper.RISING_SECTION_TITLES)):
        chosen = None
        for title in titles:
            heading = scraper._find_section_by_title(soup, title)
            if heading:
                chosen = (title, heading)
                break
        if not chosen:
            print(f"  [{label}] no heading matched in {titles}")
            continue
        title, heading = chosen
        root = scraper._find_section_root(heading, scraper.LINK_PATTERNS)
        if not root:
            print(f"  [{label}] heading={title!r} - no anchor section root, falling back to heading.parent")
            root = heading.parent
        cards = scraper._extract_drama_cards(root, scraper.LINK_PATTERNS, skip_subtree=heading)
        print(f"  [{label}] heading={title!r} cards={len(cards)}")
        for c in cards[:3]:
            print(f"    - id={c['external_id']} name={c['drama_name']!r} link={c['link']} cover={c['cover_url']!r}")


async def main():
    for cls, url in CASES:
        try:
            dump(cls, url)
        except Exception as exc:
            print(f"{cls.__name__} ERROR: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
