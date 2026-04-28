"""
FlexTV 爬虫
官网: https://www.flextv.cc
策略:
  1. 复用基类 collect_homepage_snapshots 提取首页剧目（剧名/封面/分区位置）
  2. 并发抓取各剧 /en/episodes/ 详情页（Accept: text/html），提取：
     - 点赞数 (like_count): span.num 第一个数值
     - 收藏数 (collect_count): span.num 第二个数值
     - 标签: __NUXT_DATA__ arr[state.tag[i].tag_name] 引用链
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.config import FETCH_LIMIT
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper

_DETAIL_CONCURRENCY = 8
_IS_KNUM_RE = re.compile(r"^\d[\d.]*[KkMm]?$")


def _parse_knum(text: str) -> int:
    """将 '17.7K' / '1.2M' 解析为整数"""
    t = (text or "").strip().upper()
    try:
        if t.endswith("K"):
            return int(float(t[:-1]) * 1_000)
        if t.endswith("M"):
            return int(float(t[:-1]) * 1_000_000)
        v = float(t)
        return int(v) if v >= 1 else 0
    except (ValueError, TypeError):
        return 0


class FlexTVScraper(BaseScraper):
    platform_key = "flextv"
    platform_name = "FlexTV"
    base_url = "https://www.flextv.cc"

    HOT_SECTION_TITLES = ["Trending Now", "Most Popular", "Top in FlexTV", "Top"]
    RISING_SECTION_TITLES = ["New Release", "New Arrival", "Latest"]
    LINK_PATTERNS = ["/episodes/", "/video/", "/series/"]

    _SEO_PREFIX_RE = re.compile(r"^\s*Watch\s+", re.IGNORECASE)
    _SEO_SUFFIX_RE = re.compile(
        r"(?:\s*-\s*Short Drama Poster.*$|\s+online with subtitles.*$)",
        re.IGNORECASE,
    )
    # 专为 HTML 页面的请求头（覆盖基类默认的 application/json Accept 和含 br 的 Accept-Encoding）
    _HTML_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",  # 不含 br，否则 FlexTV 返回不含互动数的精简版页面
    }

    @property
    def supports_snapshot(self) -> bool:
        return True

    def _clean_name(self, name: str) -> str:
        if not name:
            return name
        cleaned = self._SEO_SUFFIX_RE.sub("", name).strip()
        cleaned = self._SEO_PREFIX_RE.sub("", cleaned).strip()
        return cleaned or name

    @staticmethod
    def _extract_series_id(url: str) -> Optional[str]:
        """从 /episodes/episode-N-{slug}-{series_id} 提取末尾 ID"""
        path = (url or "").split("?")[0].rstrip("/")
        m = re.search(r"-([A-Za-z0-9]{8,12})$", path)
        return m.group(1) if m else None

    # ------------------------------------------------------------------
    # 从 __NUXT_DATA__ 提取标签
    # NUXT 结构:
    #   arr[state_idx] = {'detail': N, 'tag': M, ...}
    #   arr[M] = [t1_idx, t2_idx, ...]
    #   arr[ti] = {'tag_id': X, 'tag_name': name_idx, ...}
    #   arr[name_idx] = 'Comeback'
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_tags_from_nuxt(html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        nd = soup.find("script", {"id": "__NUXT_DATA__"})
        if not nd:
            return None
        try:
            arr = json.loads(nd.get_text())
        except Exception:
            return None
        if not isinstance(arr, list):
            return None

        for el in arr:
            if not isinstance(el, dict):
                continue
            if "tag" not in el or "detail" not in el:
                continue
            tag_ref = el["tag"]
            if not isinstance(tag_ref, int) or tag_ref >= len(arr):
                continue
            tag_list = arr[tag_ref]
            if not isinstance(tag_list, list) or not tag_list:
                continue

            names: List[str] = []
            for item_ref in tag_list:
                if not isinstance(item_ref, int) or item_ref >= len(arr):
                    continue
                tag_obj = arr[item_ref]
                if not isinstance(tag_obj, dict):
                    continue
                # FlexTV 用 tag_name 作为名称字段的键
                name_ref = tag_obj.get("tag_name") or tag_obj.get("name")
                if isinstance(name_ref, int) and name_ref < len(arr):
                    name = arr[name_ref]
                elif isinstance(name_ref, str):
                    name = name_ref
                else:
                    continue
                if (
                    isinstance(name, str)
                    and 2 <= len(name) <= 35
                    and not name.startswith("http")
                    and "/" not in name
                    and "{" not in name
                    # 排除纯 ID（10位小写字母数字组合）
                    and not re.fullmatch(r"[a-z0-9]{8,12}", name)
                ):
                    names.append(name)
            if names:
                return ", ".join(names)
        return None

    # ------------------------------------------------------------------
    # 解析单个详情页 HTML
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_detail_html(html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        # 点赞数 / 收藏数（仅取符合 K/M 格式的 span.num）
        valid_nums = [
            _parse_knum(el.get_text(strip=True))
            for el in soup.select("span.num")
            if _IS_KNUM_RE.match(el.get_text(strip=True))
        ]
        like_count = valid_nums[0] if valid_nums else 0
        collect_count = valid_nums[1] if len(valid_nums) > 1 else 0

        tags = FlexTVScraper._extract_tags_from_nuxt(html)
        return {"like_count": like_count, "collect_count": collect_count, "tags": tags}

    # ------------------------------------------------------------------
    # 并发抓取详情页
    # ------------------------------------------------------------------
    async def _fetch_all_details(
        self, cards: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        results: Dict[str, Dict[str, Any]] = {}

        async def fetch_one(card: Dict[str, Any]) -> None:
            series_id = card["series_id"]
            detail_url = card["link"]  # 直接使用原始 URL，/en/ 路径会导致 SSR 数据为空

            async with sem:
                # 用 HTML Accept 头，避免服务器返回 JSON 版本
                html = await self.fetch_html(
                    detail_url,
                    headers=self._HTML_HEADERS,
                    use_proxy=bool(self.proxy_pool),
                )
                results[series_id] = (
                    self._parse_detail_html(html) if html else {}
                )

        await asyncio.gather(*[fetch_one(c) for c in cards])
        return results

    # ------------------------------------------------------------------
    # 主 snapshot
    # ------------------------------------------------------------------
    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        # 1. 首页 HTML 提取剧目（复用基类，正确处理 img alt / noscript / slug fallback）
        base_snaps = await self.collect_homepage_snapshots(
            self.HOT_SECTION_TITLES,
            self.RISING_SECTION_TITLES,
            self.LINK_PATTERNS,
        )
        if not base_snaps:
            return []

        # 2. 从链接提取 series_id，组装 cards
        cards: List[Dict[str, Any]] = []
        seen_ids: set = set()
        for snap in base_snaps:
            link = snap.link or ""
            series_id = self._extract_series_id(link)
            if not series_id or series_id in seen_ids:
                continue
            seen_ids.add(series_id)
            cards.append({
                "series_id": series_id,
                "drama_name": self._clean_name(snap.drama_name),
                "cover_url": snap.cover_url,
                "link": link,
                "play_num_synth": snap.play_num,
                "collect_num_synth": snap.collect_num,
            })

        # 3. 并发抓取详情页（点赞数/收藏数/标签）
        detail_map = await self._fetch_all_details(cards[:max(FETCH_LIMIT, 50)])

        # 4. 组装 DramaSnapshot
        snapshots: List[DramaSnapshot] = []
        for card in cards[:max(FETCH_LIMIT, 50)]:
            series_id = card["series_id"]
            detail = detail_map.get(series_id, {})
            like_count = detail.get("like_count") or card["play_num_synth"]
            collect_count = detail.get("collect_count") or card["collect_num_synth"]
            snapshots.append(
                DramaSnapshot(
                    platform=self.platform_key,
                    external_id=series_id,
                    drama_name=card["drama_name"],
                    cover_url=card["cover_url"],
                    link=card["link"],
                    tags=detail.get("tags"),
                    play_num=like_count,
                    collect_num=collect_count,
                )
            )
        return snapshots

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
