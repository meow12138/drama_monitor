"""
DramaBox 爬虫
官网: https://www.dramabox.com
策略:
  1. 首页 SSR 卡片解析（链接格式 /drama/{id}/{slug}，标签格式 /browse/{id}）
  2. 并发抓取各剧详情页 __NEXT_DATA__.props.pageProps.bookInfo：
       viewCount   → play_num  (播放量，真实数值，如 2.5 亿)
       followCount → collect_num (收藏量，真实数值，如 717 万)
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from app.config import FETCH_LIMIT
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper

_DETAIL_CONCURRENCY = 6


class DramaBoxScraper(BaseScraper):
    platform_key = "dramabox"
    platform_name = "DramaBox"
    base_url = "https://www.dramabox.com"

    HOT_SECTION_TITLES = ["Must-sees", "Trending", "Hidden Gems", "Most Popular", "Top", "Hot"]
    RISING_SECTION_TITLES = ["New Release", "New Arrival", "Latest"]
    LINK_PATTERNS = ["/drama/", "/series/", "/play/", "/episode/"]
    TAG_PATTERNS = ["/browse/"]

    @property
    def supports_snapshot(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # 从 __NEXT_DATA__ 提取 bookId → cover URL 映射
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_cover_map_from_next_data(html: str) -> Dict[str, str]:
        """解析首页 __NEXT_DATA__ JSON，返回 {bookId: cover_url}"""
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not m:
            return {}
        try:
            nd = json.loads(m.group(1))
            props = nd["props"]["pageProps"]
            cover_map: Dict[str, str] = {}
            for item in props.get("bigList") or []:
                book_id = str(item.get("bookId") or "")
                cover = item.get("cover") or ""
                if book_id and cover:
                    cover_map[book_id] = cover
            for section in props.get("smallData") or []:
                for item in section.get("items") or []:
                    book_id = str(item.get("bookId") or "")
                    cover = item.get("cover") or ""
                    if book_id and cover:
                        cover_map[book_id] = cover
            return cover_map
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # 详情页: 从 __NEXT_DATA__ 提取 viewCount / followCount
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_detail_metrics(html: str) -> Dict[str, int]:
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not m:
            return {}
        try:
            nd = json.loads(m.group(1))
            book_info = nd["props"]["pageProps"]["bookInfo"]
            return {
                "view": int(book_info.get("viewCount") or 0),
                "follow": int(book_info.get("followCount") or 0),
            }
        except Exception:
            return {}

    async def _fetch_detail_metrics(
        self, snapshots: List[DramaSnapshot]
    ) -> Dict[str, Dict[str, int]]:
        """并发抓取各剧详情页，返回 {external_id: {view, follow}}"""
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        results: Dict[str, Dict[str, int]] = {}

        async def fetch_one(snap: DramaSnapshot) -> None:
            if not snap.link:
                return
            async with sem:
                html = await self.fetch_html(snap.link, use_proxy=bool(self.proxy_pool))
            if html:
                metrics = self._parse_detail_metrics(html)
                if metrics:
                    results[snap.external_id] = metrics

        await asyncio.gather(*[fetch_one(s) for s in snapshots], return_exceptions=True)
        return results

    # ------------------------------------------------------------------
    # fetch_snapshot
    # ------------------------------------------------------------------

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        # 1. 首页解析（带链接、标签、位置推算的 play_num/collect_num）
        base_snaps = await self.collect_homepage_snapshots(
            self.HOT_SECTION_TITLES,
            self.RISING_SECTION_TITLES,
            self.LINK_PATTERNS,
            tag_patterns=self.TAG_PATTERNS,
        )
        if not base_snaps:
            return []

        # 2. 从 __NEXT_DATA__ 补全封面：首页 <img> 大量使用 Next.js blur 占位图，
        #    真实封面 URL 在 JSON 里
        cover_map: Dict[str, str] = {}
        try:
            homepage_html = await self.fetch_html(self.base_url, use_proxy=bool(self.proxy_pool))
            if homepage_html:
                cover_map = self._extract_cover_map_from_next_data(homepage_html)
        except Exception as exc:
            print(f"[dramabox] cover map extraction failed: {exc}")

        # 3. 并发抓取详情页，填入真实播放量 / 收藏量
        metrics_map: Dict[str, Dict[str, int]] = {}
        try:
            metrics_map = await self._fetch_detail_metrics(
                base_snaps[: max(FETCH_LIMIT, 20)]
            )
            hit = sum(1 for v in metrics_map.values() if v.get("view", 0) > 0)
            print(f"[dramabox] detail metrics: {hit}/{len(base_snaps)} got real viewCount")
        except Exception as exc:
            print(f"[dramabox] detail metrics failed, using fallback: {exc}")

        # 4. 用真实数据替换位置推算值，并补全封面
        final: List[DramaSnapshot] = []
        for snap in base_snaps:
            real = metrics_map.get(snap.external_id, {})
            view = real.get("view", 0)
            follow = real.get("follow", 0)
            cover = snap.cover_url or cover_map.get(snap.external_id)
            final.append(
                DramaSnapshot(
                    platform=snap.platform,
                    external_id=snap.external_id,
                    drama_name=snap.drama_name,
                    cover_url=cover,
                    link=snap.link,
                    tags=snap.tags,
                    play_num=view if view > 0 else snap.play_num,
                    collect_num=follow if follow > 0 else snap.collect_num,
                )
            )
        return final

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []

