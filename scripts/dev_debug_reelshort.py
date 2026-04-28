"""调试 ReelShort 的卡片提取过程"""
import asyncio

import httpx
from bs4 import BeautifulSoup

from app.scrapers.reelshort import ReelShortScraper


async def main():
    scraper = ReelShortScraper()
    html = httpx.get(
        "https://www.reelshort.com",
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=20,
    ).text
    soup = BeautifulSoup(html, "html.parser")
    heading = scraper._find_section_by_title(soup, "New Release")
    root = scraper._find_section_root(heading, scraper.LINK_PATTERNS)
    print("section_root:", root.name if root else None, "class:", root.get("class") if root else None)
    all_titles = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"]) if h.get_text(strip=True)]
    print("all_section_titles:", len(all_titles), all_titles[:6])
    cards = scraper._extract_drama_cards(
        root, scraper.LINK_PATTERNS, skip_subtree=heading, section_titles=all_titles
    )
    print(f"extracted cards: {len(cards)}")
    for c in cards[:3]:
        print("  ", c)
    cards_no_titles = scraper._extract_drama_cards(
        root, scraper.LINK_PATTERNS, skip_subtree=heading, section_titles=None
    )
    print(f"extracted cards (no section_titles): {len(cards_no_titles)}")
    for c in cards_no_titles[:3]:
        print("  ", c)


if __name__ == "__main__":
    asyncio.run(main())
