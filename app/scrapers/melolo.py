"""
Melolo 爬虫
官网: https://melolo.com
策略:
  1. 首页 SSR（Next.js App Router）解析剧目卡片
  2. 并发抓取各剧详情页，从 /category/ 链接提取完整标签列表
     详情页示例: /dramas/fated-to-find-you
     标签来源: <a href="/category/romance">Romance</a> 等
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.config import FETCH_LIMIT
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper

_DETAIL_CONCURRENCY = 8


class MeloloScraper(BaseScraper):
    platform_key = "melolo"
    platform_name = "Melolo"
    base_url = "https://melolo.com"

    HOT_SECTION_TITLES = [
        "Top Short Drama Lists",
        "Popular Romance Mini-Series",
        "Popular",
        "Top",
    ]
    RISING_SECTION_TITLES = [
        "Latest Mini-Series Releases",
        "Latest",
        "New Release",
    ]
    LINK_PATTERNS = ["/dramas/", "/drama/", "/series/", "/episode/"]

    @property
    def supports_snapshot(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # 详情页: 从 /category/ 链接提取完整标签
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_detail_tags(html: str) -> Optional[str]:
        """从详情页提取所有 /category/ 链接的文本作为标签"""
        soup = BeautifulSoup(html, "html.parser")
        seen: list[str] = []
        for a in soup.find_all("a", href=re.compile(r"/category/")):
            text = a.get_text(strip=True)
            if text and text not in seen and 2 <= len(text) <= 30:
                seen.append(text)
        return ", ".join(seen) if seen else None

    async def _enrich_tags(
        self, snapshots: List[DramaSnapshot]
    ) -> List[DramaSnapshot]:
        """并发抓取详情页，填入完整标签；无标签的剧保留原有单标签"""
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        tag_map: Dict[str, Optional[str]] = {}

        async def fetch_one(snap: DramaSnapshot) -> None:
            if not snap.link:
                return
            # 把 /ep1 这类集数后缀去掉，取剧集主页
            detail_url = re.sub(r"/ep\d+$", "", snap.link.rstrip("/"))
            async with sem:
                html = await self.fetch_html(
                    detail_url, use_proxy=bool(self.proxy_pool)
                )
            if html:
                tags = self._parse_detail_tags(html)
                if tags:
                    tag_map[snap.external_id] = tags

        await asyncio.gather(*[fetch_one(s) for s in snapshots], return_exceptions=True)

        enriched = []
        for snap in snapshots:
            rich_tags = tag_map.get(snap.external_id)
            enriched.append(
                DramaSnapshot(
                    platform=snap.platform,
                    external_id=snap.external_id,
                    drama_name=snap.drama_name,
                    cover_url=snap.cover_url,
                    link=snap.link,
                    tags=rich_tags or snap.tags,   # 优先用详情页全标签
                    play_num=snap.play_num,
                    collect_num=snap.collect_num,
                )
            )
        return enriched

    # ------------------------------------------------------------------
    # fetch_snapshot
    # ------------------------------------------------------------------

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        # 1. 首页解析
        base_snaps = await self.collect_homepage_snapshots(
            self.HOT_SECTION_TITLES,
            self.RISING_SECTION_TITLES,
            self.LINK_PATTERNS,
        )
        if not base_snaps:
            return []

        # 2. 并发抓取详情页，填充完整标签
        try:
            enriched = await self._enrich_tags(base_snaps[: max(FETCH_LIMIT, 25)])
            hit = sum(1 for s in enriched if s.tags)
            print(f"[melolo] tags enriched: {hit}/{len(enriched)} dramas have tags")
            return enriched
        except Exception as exc:
            print(f"[melolo] tag enrichment failed: {exc}")
            return base_snaps

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
