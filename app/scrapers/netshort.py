"""
NetShort 爬虫
官网: https://netshort.com（麦芽文化 / Maiya Culture）

实现说明:
1. NetShort 是 Next.js App Router (RSC) 站点，其首页 SSR 已直接渲染剧集卡片。
2. 暂不解 self.__next_f.push 的 RSC 流，直接用 BeautifulSoup 解析 HTML。
3. 主页含 5 个分区，本爬虫只取最有信号的两个：
     - "Trending Now" -> 用于 hot 榜
     - "New Releases" -> 用于 rising 榜
4. 详情页内嵌 JSON 含 totalLikeNums（心形点赞）和 totalChaseNums（书签收藏），
   并发抓取后分别填入 play_num / collect_num。
   抓取失败时回退到分区位置推算值。
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.config import FETCH_LIMIT
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper

_DETAIL_CONCURRENCY = 8


def _parse_knum(text: str) -> int:
    """将 '23.4K' → 23400，'1.2M' → 1200000，'500' → 500，失败返回 0"""
    t = (text or "").strip().upper().replace(",", "")
    try:
        if t.endswith("K"):
            return int(float(t[:-1]) * 1_000)
        if t.endswith("M"):
            return int(float(t[:-1]) * 1_000_000)
        v = float(t)
        return int(v) if v >= 1 else 0
    except (ValueError, TypeError):
        return 0


class NetShortScraper(BaseScraper):
    platform_key = "netshort"
    platform_name = "NetShort"
    base_url = "https://netshort.com"

    HOT_SECTION = "Trending Now"
    RISING_SECTION = "New Releases"

    @property
    def supports_snapshot(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # 首页卡片解析
    # ------------------------------------------------------------------

    def _parse_section_items(
        self, soup: BeautifulSoup, section_title: str
    ) -> List[Dict[str, Any]]:
        heading = soup.find(
            lambda tag: tag.name == "h2"
            and tag.get_text(" ", strip=True) == section_title
        )
        if not heading:
            return []

        section = heading.find_parent("section")
        if not section:
            return []

        items: List[Dict[str, Any]] = []
        for card in section.select("div.carousel-item"):
            cover_img = card.select_one("img.list-item-img")
            name_el = card.select_one(".list-item-info-name")
            episode_link = card.select_one("a[href*='/episode/']")
            tag_links = card.select("a[href*='/drama/']")

            episode_href = episode_link.get("href") if episode_link else None
            cover_url = cover_img.get("src") if cover_img else None
            drama_name = (
                name_el.get_text(" ", strip=True)
                if name_el
                else (cover_img.get("alt") if cover_img else "")
            )

            external_id = self._extract_external_id(episode_href) if episode_href else None
            tags = [a.get_text(" ", strip=True) for a in tag_links if a.get_text(strip=True)]

            if not drama_name or not external_id:
                continue

            items.append(
                {
                    "external_id": external_id,
                    "drama_name": drama_name.strip(),
                    "cover_url": cover_url,
                    "link": self._absolute_link(episode_href),
                    "tags": tags,
                }
            )
        return items

    def _extract_external_id(self, href: str) -> Optional[str]:
        # /episode/the-ceos-custom-game-of-desire-2045032067044999170 -> 2045032067044999170
        match = re.search(r"-(\d{6,})/?$", href)
        if match:
            return match.group(1)
        return None

    def _absolute_link(self, href: Optional[str]) -> Optional[str]:
        if not href:
            return None
        if href.startswith("http"):
            return href
        return f"{self.base_url.rstrip('/')}{href}"

    # ------------------------------------------------------------------
    # 详情页抓取：提取真实点赞数 / 收藏数
    # ------------------------------------------------------------------

    def _parse_detail_html(self, html: str) -> Dict[str, int]:
        """
        从详情页 HTML 提取 like / collect 数值。
        优先从页面内嵌 JSON（totalLikeNums / totalChaseNums）读取；
        备选从 <span class="ml-[0.4375rem]"> 顺序读取。
        """
        like_m = re.search(r'"totalLikeNums":"([^"]+)"', html)
        collect_m = re.search(r'"totalChaseNums":"([^"]+)"', html)
        if like_m or collect_m:
            return {
                "like": _parse_knum(like_m.group(1) if like_m else "0"),
                "collect": _parse_knum(collect_m.group(1) if collect_m else "0"),
            }

        # 备选：BeautifulSoup 解析 span 顺序
        soup = BeautifulSoup(html, "html.parser")
        knum_re = re.compile(r"^\d[\d.]*[KkMm]?$")
        spans = [
            el.get_text(strip=True)
            for el in soup.find_all("span")
            if knum_re.match(el.get_text(strip=True))
            and "ml-" in " ".join(el.get("class", []))
        ]
        return {
            "like": _parse_knum(spans[0]) if spans else 0,
            "collect": _parse_knum(spans[1]) if len(spans) > 1 else 0,
        }

    async def _fetch_detail_metrics(
        self, items: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, int]]:
        """
        并发抓取详情页，返回 {external_id: {"like": N, "collect": N}}
        """
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        results: Dict[str, Dict[str, int]] = {}

        async def fetch_one(item: Dict[str, Any]) -> None:
            ext_id = item["external_id"]
            link = item.get("link") or ""
            if not link:
                return
            async with sem:
                html = await self.fetch_html(link, use_proxy=bool(self.proxy_pool))
            if html:
                results[ext_id] = self._parse_detail_html(html)

        await asyncio.gather(*[fetch_one(it) for it in items], return_exceptions=True)
        return results

    # ------------------------------------------------------------------
    # 快照合并
    # ------------------------------------------------------------------

    def _merge_into_snapshots(
        self,
        hot_items: List[Dict[str, Any]],
        rising_items: List[Dict[str, Any]],
        metrics_map: Optional[Dict[str, Dict[str, int]]] = None,
    ) -> List[DramaSnapshot]:
        """合并两个分区的卡片，优先使用详情页真实指标，回退到位置推算值"""
        hot_count = len(hot_items)
        rising_count = len(rising_items)

        merged: Dict[str, Dict[str, Any]] = {}

        for idx, item in enumerate(hot_items):
            ext_id = item["external_id"]
            entry = merged.setdefault(ext_id, dict(item))
            entry["play_num_synth"] = max(0, hot_count - idx)
            entry.setdefault("collect_num_synth", 0)

        for idx, item in enumerate(rising_items):
            ext_id = item["external_id"]
            entry = merged.setdefault(ext_id, dict(item))
            entry["collect_num_synth"] = max(0, rising_count - idx)
            entry.setdefault("play_num_synth", 0)
            for tag in item.get("tags", []):
                if tag not in entry.get("tags", []):
                    entry.setdefault("tags", []).append(tag)

        mm = metrics_map or {}
        snapshots: List[DramaSnapshot] = []
        for entry in list(merged.values())[: max(FETCH_LIMIT, hot_count, rising_count)]:
            tags_value = ", ".join(entry.get("tags") or []) or None
            ext_id = entry["external_id"]
            real = mm.get(ext_id, {})
            like_count = real.get("like", 0)
            collect_count = real.get("collect", 0)
            snapshots.append(
                DramaSnapshot(
                    platform=self.platform_key,
                    external_id=ext_id,
                    drama_name=entry["drama_name"],
                    cover_url=entry.get("cover_url"),
                    link=entry.get("link"),
                    tags=tags_value,
                    play_num=like_count if like_count > 0 else int(entry.get("play_num_synth", 0)),
                    collect_num=collect_count if collect_count > 0 else int(entry.get("collect_num_synth", 0)),
                )
            )
        return snapshots

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        html = await self.fetch_html(self.base_url, use_proxy=bool(self.proxy_pool))
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        hot_items = self._parse_section_items(soup, self.HOT_SECTION)
        rising_items = self._parse_section_items(soup, self.RISING_SECTION)
        if not hot_items and not rising_items:
            return []

        # 去重合并所有卡片，并发抓取详情页真实指标
        all_items: Dict[str, Dict[str, Any]] = {}
        for it in hot_items + rising_items:
            all_items.setdefault(it["external_id"], it)

        metrics_map: Dict[str, Dict[str, int]] = {}
        try:
            metrics_map = await self._fetch_detail_metrics(
                list(all_items.values())[: max(FETCH_LIMIT, 50)]
            )
            hit = sum(1 for v in metrics_map.values() if v.get("like", 0) > 0)
            print(
                f"[netshort] detail metrics: {hit}/{len(all_items)} got real like_count"
            )
        except Exception as exc:
            print(f"[netshort] detail metrics fetch failed, using fallback: {exc}")

        return self._merge_into_snapshots(hot_items, rising_items, metrics_map)

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
