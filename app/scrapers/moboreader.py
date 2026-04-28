"""
MoboReader 爬虫
官网: https://www.moboreader.com
策略: 首页若可达即用 SSR 卡片解析；当前网络下连接被重置，
需配置 PROXY_POOL 后才可使用。
"""

from typing import List

from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper


class MoboReaderScraper(BaseScraper):
    platform_key = "moboreader"
    platform_name = "MoboReader"
    base_url = "https://www.moboreader.com"

    HOT_SECTION_TITLES = ["Trending", "Most Popular", "Top", "Hot", "Recommended"]
    RISING_SECTION_TITLES = ["New Release", "New Arrival", "Latest"]
    LINK_PATTERNS = ["/drama/", "/series/", "/play/", "/episode/"]

    @property
    def supports_snapshot(self) -> bool:
        return True

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        return await self.collect_homepage_snapshots(
            self.HOT_SECTION_TITLES,
            self.RISING_SECTION_TITLES,
            self.LINK_PATTERNS,
        )

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
