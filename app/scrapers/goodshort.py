"""
GoodShort 爬虫
官网: https://www.goodshort.com
策略:
  1. POST /hwycreels/home/index 获取首页栏目列表（含 viewCount、标签）
  2. 并发调用 POST /hwycreels/book/detail 获取每部剧的详情数据：
       viewCountDisplay → play_num  (网站显示的 Views，如 30.1M)
       inLibraryNum     → collect_num (Followers 加入书架量，如 4.4M)

栏目映射:
  hot:    Top in GoodShort / Hot List
  rising: Most Trending / Popular Now
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from app.config import FETCH_LIMIT
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper

_DETAIL_CONCURRENCY = 8


def _parse_knum(text: str) -> int:
    """'30.1M' → 30100000, '4.4M' → 4400000, '9.6K' → 9600"""
    t = (text or "").strip().upper().replace(",", "")
    try:
        if t.endswith("M"):
            return int(float(t[:-1]) * 1_000_000)
        if t.endswith("K"):
            return int(float(t[:-1]) * 1_000)
        v = float(t)
        return int(v) if v >= 1 else 0
    except (ValueError, TypeError):
        return 0


class GoodShortScraper(BaseScraper):
    platform_key = "goodshort"
    platform_name = "GoodShort"
    base_url = "https://www.goodshort.com"

    HOME_API = "/hwycreels/home/index"
    DETAIL_API = "/hwycreels/book/detail"
    API_HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://www.goodshort.com/",
    }

    HOT_COLUMN_NAMES = {"Top in GoodShort", "Hot List", "Most Popular"}
    RISING_COLUMN_NAMES = {"Most Trending", "Popular Now", "New Release"}

    HOT_SECTION_TITLES = ["Most Trending", "Top in GoodShort", "Hot List", "Trending"]
    RISING_SECTION_TITLES = ["New Release", "New Arrival", "Latest", "Just Added"]
    LINK_PATTERNS = ["/dramas/", "/drama/", "/series/", "/play/"]

    @property
    def supports_snapshot(self) -> bool:
        return True

    def _build_link(self, raw: Dict[str, Any]) -> Optional[str]:
        slug = raw.get("bookResourceUrl") or ""
        if slug:
            return f"{self.base_url}/drama/{slug}"
        source_id = raw.get("sourceId") or raw.get("bookId") or ""
        if source_id:
            return f"{self.base_url}/drama/{source_id}"
        return None

    def _build_cover_url(self, raw: Dict[str, Any]) -> Optional[str]:
        return raw.get("cover") or raw.get("bannerUrl") or None

    def _build_tags(self, raw: Dict[str, Any]) -> Optional[str]:
        tag_names = [t["name"] for t in (raw.get("tagsList") or []) if t.get("name")]
        if not tag_names:
            tag_names = [g["name"] for g in (raw.get("genreList") or []) if g.get("name")]
        return ", ".join(tag_names) if tag_names else None

    # ------------------------------------------------------------------
    # API 调用
    # ------------------------------------------------------------------

    async def _post_api(self, path: str, payload: dict) -> Optional[Dict[str, Any]]:
        if not self._client:
            raise RuntimeError("Scraper must be used as async context manager")
        await self._delay()
        try:
            response = await self._client.post(
                self.base_url + path,
                headers={**self._get_default_headers(), **self.API_HEADERS},
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            print(f"[{self.platform_key}] POST {path} failed: {exc}")
            return None

    async def _fetch_home_columns(self) -> List[Dict[str, Any]]:
        data = await self._post_api(self.HOME_API, {})
        return (data.get("data") or {}).get("pageColumns") or [] if data else []

    async def _fetch_column_full(self, column_id: int) -> List[Dict[str, Any]]:
        data = await self._post_api(
            "/hwycreels/home/second/list",
            {"columnId": column_id, "page": 1, "pageSize": 20},
        )
        if data and data.get("data"):
            col_data = data["data"]
            if isinstance(col_data, dict):
                return col_data.get("items") or []
        return []

    async def _fetch_book_detail(self, source_id: str) -> Dict[str, Any]:
        """调用 /hwycreels/book/detail 获取 viewCountDisplay 和 inLibraryNum"""
        data = await self._post_api(self.DETAIL_API, {"bookId": source_id})
        if data and data.get("data"):
            return data["data"].get("book") or {}
        return {}

    async def _enrich_snapshots(
        self, snapshots: List[DramaSnapshot]
    ) -> List[DramaSnapshot]:
        """并发抓取各剧详情 API，填入 Views（play_num）和 Followers（collect_num）"""
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        detail_map: Dict[str, Dict[str, Any]] = {}

        async def fetch_one(snap: DramaSnapshot) -> None:
            async with sem:
                book = await self._fetch_book_detail(snap.external_id)
            if book:
                detail_map[snap.external_id] = book

        await asyncio.gather(*[fetch_one(s) for s in snapshots], return_exceptions=True)

        enriched = []
        for snap in snapshots:
            book = detail_map.get(snap.external_id, {})
            # viewCountDisplay: "30.1M" → 播放量
            view_display = book.get("viewCountDisplay") or ""
            play_num = _parse_knum(view_display) if view_display else snap.play_num
            # inLibraryNum: 4432143 → 收藏量
            in_library = int(book.get("inLibraryNum") or 0)
            collect_num = in_library if in_library > 0 else snap.collect_num

            enriched.append(
                DramaSnapshot(
                    platform=snap.platform,
                    external_id=snap.external_id,
                    drama_name=snap.drama_name,
                    cover_url=snap.cover_url,
                    link=snap.link,
                    tags=snap.tags,
                    play_num=play_num,
                    collect_num=collect_num,
                )
            )
        return enriched

    # ------------------------------------------------------------------
    # fetch_snapshot
    # ------------------------------------------------------------------

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        # 1. 首页栏目数据
        columns = await self._fetch_home_columns()
        if not columns:
            return await self.collect_homepage_snapshots(
                self.HOT_SECTION_TITLES,
                self.RISING_SECTION_TITLES,
                self.LINK_PATTERNS,
            )

        merged: Dict[str, Dict[str, Any]] = {}
        for col in columns:
            col_name = col.get("name") or ""
            col_id = col.get("id")
            is_hot = col_name in self.HOT_COLUMN_NAMES
            is_rising = col_name in self.RISING_COLUMN_NAMES
            if not (is_hot or is_rising) or not col_id:
                continue

            items = await self._fetch_column_full(col_id)
            if not items:
                items = col.get("items") or []

            col_count = len(items)
            for idx, item in enumerate(items):
                source_id = str(item.get("sourceId") or item.get("bookId") or "")
                if not source_id:
                    continue
                view_count = int(item.get("viewCount") or 0)
                entry = merged.setdefault(source_id, {
                    "source_id": source_id,
                    "book_name": item.get("bookName") or item.get("name") or "",
                    "cover_url": self._build_cover_url(item),
                    "link": self._build_link(item),
                    "tags": self._build_tags(item),
                    "play_num": 0,
                    "collect_num": 0,
                })
                if is_hot:
                    entry["play_num"] = max(entry["play_num"], view_count)
                    entry["collect_num"] = max(entry.get("collect_num", 0), max(0, col_count - idx))
                else:
                    entry["collect_num"] = max(entry.get("collect_num", 0), max(0, col_count - idx))
                    if not entry["play_num"]:
                        entry["play_num"] = view_count

        base_snaps = [
            DramaSnapshot(
                platform=self.platform_key,
                external_id=entry["source_id"],
                drama_name=entry["book_name"],
                cover_url=entry["cover_url"],
                link=entry["link"],
                tags=entry["tags"],
                play_num=entry["play_num"],
                collect_num=entry["collect_num"],
            )
            for entry in list(merged.values())[:max(FETCH_LIMIT, 100)]
            if entry.get("book_name")
        ]

        # 2. 并发抓取详情 API，替换 Views 和 Followers 真实数据
        try:
            enriched = await self._enrich_snapshots(base_snaps)
            hit_view = sum(1 for s in enriched if (s.play_num or 0) > 1_000_000)
            hit_collect = sum(1 for s in enriched if (s.collect_num or 0) > 1_000_000)
            print(f"[goodshort] detail enriched: view>{1}M={hit_view}, collect>{1}M={hit_collect}")
            return enriched
        except Exception as exc:
            print(f"[goodshort] detail enrichment failed: {exc}")
            return base_snaps

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
