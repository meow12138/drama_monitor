import asyncio

from app.scrapers.melolo import MeloloScraper


async def main():
    async with MeloloScraper() as scraper:
        snaps = await scraper.fetch_snapshot()
        print("total:", len(snaps))
        for s in snaps:
            print(
                "-",
                s.drama_name[:50],
                "| cover:",
                bool(s.cover_url),
                "| link:",
                bool(s.link),
                "| tags:",
                s.tags,
            )


if __name__ == "__main__":
    asyncio.run(main())
