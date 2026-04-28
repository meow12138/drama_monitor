"""
ReelShort 爬虫
官网: https://www.reelshort.com
策略: 使用 Web API 获取真实播放量/收藏量
  - GET /api/video/book/getTagBook?language=en&page=N&page_size=50 → 含 read_count / collect_count
  - GET /api/video/book/getNewTagBook?language=en&page=N&page_size=50&tagId=xxx → 最新剧集
  - 首次调用提取 buildId 并通过 /_next/data/{buildId}/index.json 获取首页 banner 数据
"""

import asyncio
import math
import re
from typing import Any, Dict, List, Optional

from app.config import FETCH_LIMIT, MAX_RETRIES, RETRY_BACKOFF
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper


class ReelShortScraper(BaseScraper):
    platform_key = "reelshort"
    platform_name = "ReelShort"
    base_url = "https://www.reelshort.com"

    API_HEADERS = {
        "Accept": "application/json",
        "Referer": "https://www.reelshort.com/",
    }
    PAGE_SIZE = 50
    MAX_PAGES = max(2, math.ceil(FETCH_LIMIT / 50))

    # HTML fallback（API 不可用时使用）
    HOT_SECTION_TITLES = ["Most Popular", "Trending", "Hot List", "Top in"]
    RISING_SECTION_TITLES = ["New Release", "New Arrival", "Latest", "Just Added"]
    LINK_PATTERNS = ["/episodes/", "/episode/", "/drama/", "/play/"]

    @property
    def supports_snapshot(self) -> bool:
        return True

    def _slugify(self, title: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", (title or "").strip().lower()).strip("-")
        return slug[:80]

    def _build_link(self, raw: Dict[str, Any]) -> Optional[str]:
        _id = raw.get("_id") or ""
        chapter_id = raw.get("chapter_id") or ""
        title = raw.get("book_title") or ""
        serial_num = raw.get("serial_number") or 1
        if not chapter_id or not title or not _id:
            return None
        slug = self._slugify(title)
        # 当前 URL 格式: /episodes/episode-{n}-{slug}-{_id}-{chapter_id}
        return f"{self.base_url}/episodes/episode-{serial_num}-{slug}-{_id}-{chapter_id}"

    def _build_tags(self, raw: Dict[str, Any]) -> Optional[str]:
        tags = raw.get("tag") or []
        if isinstance(tags, list):
            return ", ".join(str(t) for t in tags if t) or None
        return str(tags) if tags else None

    async def _fetch_tag_books(self, page: int) -> List[Dict[str, Any]]:
        """GET /api/video/book/getTagBook - 返回含 read_count/collect_count 的书单"""
        url = f"{self.base_url}/api/video/book/getTagBook"
        params = {"language": "en", "page": page, "page_size": self.PAGE_SIZE}
        data = await self.fetch_json(url, headers=self.API_HEADERS, params=params, use_proxy=False)
        if data and data.get("code") == 0:
            return (data.get("data") or {}).get("books") or []
        return []

    async def _fetch_new_tag_books(self, page: int, tag_id: str = "") -> List[Dict[str, Any]]:
        """GET /api/video/book/getNewTagBook - 返回最新剧集"""
        url = f"{self.base_url}/api/video/book/getNewTagBook"
        params = {"language": "en", "page": page, "page_size": self.PAGE_SIZE, "tagId": tag_id}
        data = await self.fetch_json(url, headers=self.API_HEADERS, params=params, use_proxy=False)
        if data and data.get("code") == 0:
            return (data.get("data") or {}).get("books") or []
        return []

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        """通过 getTagBook API 抓取全量剧集快照（含真实 read_count / collect_count）"""
        # 多页拉取剧集列表
        all_books: Dict[str, Dict[str, Any]] = {}
        for page in range(1, self.MAX_PAGES + 1):
            books = await self._fetch_tag_books(page)
            if not books:
                break
            for book in books:
                bid = book.get("_id") or book.get("t_book_id") or ""
                if bid and bid not in all_books:
                    all_books[bid] = book
            if len(books) < self.PAGE_SIZE:
                break
            await asyncio.sleep(0.3)

        if not all_books:
            # API 不可达，回退到 HTML 解析
            return await self.collect_homepage_snapshots(
                self.HOT_SECTION_TITLES,
                self.RISING_SECTION_TITLES,
                self.LINK_PATTERNS,
            )

        snapshots: List[DramaSnapshot] = []
        for bid, raw in list(all_books.items())[:max(FETCH_LIMIT, 100)]:
            title = raw.get("book_title") or ""
            if not title:
                continue
            cover_url = raw.get("book_pic") or None
            link = self._build_link(raw)
            tags = self._build_tags(raw)
            read_count = raw.get("read_count") or 0
            collect_count = raw.get("collect_count") or 0

            snapshots.append(
                DramaSnapshot(
                    platform=self.platform_key,
                    external_id=bid,
                    drama_name=title,
                    cover_url=cover_url,
                    link=link,
                    tags=tags,
                    play_num=int(read_count),
                    collect_num=int(collect_count),
                )
            )
        return snapshots

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
