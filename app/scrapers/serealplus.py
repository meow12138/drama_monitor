"""
Sereal+ 爬虫
官网: https://www.sereal.plus（重定向到 sereal.com）

策略: 解析首页最大 inline script 中的 Nuxt SSR 数据数组
  - 数组格式: ["ShallowReactive",1], {数据对象}, ...
  - 每个 drama 记录: {contentId, contentName, url(封面), classList(标签), ...}
  - 每个栏目 column: {columnName, records: [剧索引列表], ...}

字段映射:
  contentId     → external_id
  contentName   → drama_name
  url           → cover_url (封面图)
  classList     → tags (类型标签)
  columnName    → 判断 hot / rising 分区
  link          → https://www.sereal.com/detail/{contentId}

真实指标获取（两步 API，无需登录）:
  Step 1: GET /content/video/chapter/list?contentId={cid}&page=1&size=1
          → records[0].id = firstChapterId
  Step 2: GET /content/video/chapter/behavior?contentId={cid}&chapterId={firstChapterId}
          → data.thumbUpNum = Like 数（"0.6M"）
          → data.collectNum = Collect 数（"2.4M"）
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.config import FETCH_LIMIT
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper

# 分区标题关键词
_HOT_KEYWORDS = {"trending", "popular", "top", "hot", "must"}
_RISING_KEYWORDS = {"new", "arrival", "latest", "added", "fresh", "release"}

# Sereal+ 独立 REST API（不同于首页域名）
_API_BASE = "https://web-api.serealplus.com"
_API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*",
    "Referer": "https://www.sereal.com/",
    "Origin": "https://www.sereal.com",
    "Accept-Language": "en-US,en;q=0.9",
}
# 并发度：同时向 API 发送的请求数上限
_DETAIL_SEMAPHORE_SIZE = 5
_DETAIL_TIMEOUT = 12.0


def _deref(arr: list, ref: Any) -> Any:
    """解引用 Nuxt 数组中的索引"""
    if isinstance(ref, int) and 0 <= ref < len(arr):
        return arr[ref]
    return ref


def _parse_metric_str(s: Any) -> int:
    """将 '0.6M' → 600000, '2.4M' → 2400000, '1.2K' → 1200, '123' → 123"""
    if s is None:
        return 0
    text = str(s).strip()
    try:
        upper = text.upper()
        if upper.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        if upper.endswith("K"):
            return int(float(text[:-1]) * 1_000)
        return int(float(text))
    except (ValueError, TypeError):
        return 0


class SerealPlusScraper(BaseScraper):
    platform_key = "serealplus"
    platform_name = "Sereal+"
    base_url = "https://www.sereal.plus"

    # HTML fallback 分区标题（当 Nuxt 解析失败时）
    HOT_SECTION_TITLES = ["Most Trending", "Trending", "Top", "Hot"]
    RISING_SECTION_TITLES = ["New Arrivals", "New Release", "Latest", "Just Added"]
    LINK_PATTERNS = ["/dramas/", "/drama/", "/episode/", "/play/"]

    @property
    def supports_snapshot(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # 核心解析: Nuxt SSR 数据数组
    # ------------------------------------------------------------------
    def _parse_nuxt_array(self, arr: list) -> List[DramaSnapshot]:
        """从 Nuxt 数据数组提取所有 drama 快照（play_num/collect_num 用位置估算填充）"""

        # 第一遍：建立 array_idx → drama_dict 映射
        drama_by_idx: Dict[int, Dict[str, Any]] = {}
        for i, el in enumerate(arr):
            if not isinstance(el, dict) or "contentId" not in el or "contentName" not in el:
                continue
            content_id = _deref(arr, el.get("contentId"))
            content_name = _deref(arr, el.get("contentName"))
            if not content_id or not content_name:
                continue

            cover_url = _deref(arr, el.get("url"))
            # mBannerUrl 通常是竖版封面，优先使用
            m_banner = _deref(arr, el.get("mBannerUrl"))
            if isinstance(m_banner, str) and m_banner.startswith("http"):
                cover_url = m_banner

            # classList → 标签列表
            tags: List[str] = []
            class_list = _deref(arr, el.get("classList"))
            if isinstance(class_list, list):
                for cls_ref in class_list:
                    cls_obj = _deref(arr, cls_ref)
                    if isinstance(cls_obj, dict):
                        name = _deref(arr, cls_obj.get("name"))
                        if isinstance(name, str) and len(name) > 1 and not name.isdigit():
                            tags.append(name)

            drama_by_idx[i] = {
                "content_id": str(content_id),
                "drama_name": str(content_name),
                "cover_url": str(cover_url) if isinstance(cover_url, str) else None,
                "link": f"https://www.sereal.com/detail/{content_id}",
                "tags": tags,
                "play_num": 0,
                "collect_num": 0,
            }

        if not drama_by_idx:
            return []

        # 第二遍：找各栏目，区分 hot / rising
        hot_items: List[Dict[str, Any]] = []
        rising_items: List[Dict[str, Any]] = []
        seen_hot: set = set()
        seen_rising: set = set()

        for el in arr:
            if not isinstance(el, dict) or "columnName" not in el or "records" not in el:
                continue
            col_name = _deref(arr, el.get("columnName"))
            if not isinstance(col_name, str):
                continue
            records_ref = _deref(arr, el.get("records"))
            if not isinstance(records_ref, list):
                continue

            col_lower = col_name.lower()
            if "banner" in col_lower:
                continue  # 跳过 banner

            is_hot = any(k in col_lower for k in _HOT_KEYWORDS)
            is_rising = any(k in col_lower for k in _RISING_KEYWORDS)
            if not is_hot and not is_rising:
                continue

            for ref in records_ref:
                idx = ref if isinstance(ref, int) else None
                if idx is None:
                    continue
                # Nuxt 响应式包装: ["Reactive", actual_idx] 或 ["ShallowReactive", actual_idx]
                el_at = arr[idx] if 0 <= idx < len(arr) else None
                if (
                    isinstance(el_at, list)
                    and len(el_at) == 2
                    and isinstance(el_at[0], str)
                    and el_at[0] in ("Reactive", "ShallowReactive")
                    and isinstance(el_at[1], int)
                ):
                    idx = el_at[1]
                drama = drama_by_idx.get(idx)
                if not drama:
                    continue
                cid = drama["content_id"]
                if is_hot and cid not in seen_hot:
                    seen_hot.add(cid)
                    hot_items.append(drama)
                elif is_rising and cid not in seen_rising:
                    seen_rising.add(cid)
                    rising_items.append(drama)

        # 合并两个列表，用位置估算 play_num / collect_num（后续会被真实值覆盖）
        hot_n = len(hot_items)
        rising_n = len(rising_items)
        merged: Dict[str, Dict[str, Any]] = {}

        for idx, d in enumerate(hot_items):
            cid = d["content_id"]
            entry = merged.setdefault(cid, d.copy())
            entry["play_num"] = max(entry.get("play_num", 0), max(0, hot_n - idx))
            entry.setdefault("collect_num", 0)

        for idx, d in enumerate(rising_items):
            cid = d["content_id"]
            entry = merged.setdefault(cid, d.copy())
            entry["collect_num"] = max(entry.get("collect_num", 0), max(0, rising_n - idx))
            entry.setdefault("play_num", 0)

        snapshots: List[DramaSnapshot] = []
        for entry in list(merged.values())[:max(FETCH_LIMIT, 50)]:
            tags_str = ", ".join(entry["tags"]) if entry["tags"] else None
            snapshots.append(
                DramaSnapshot(
                    platform=self.platform_key,
                    external_id=entry["content_id"],
                    drama_name=entry["drama_name"],
                    cover_url=entry["cover_url"] or None,
                    link=entry.get("link"),
                    tags=tags_str,
                    play_num=entry.get("play_num", 0),
                    collect_num=entry.get("collect_num", 0),
                )
            )
        return snapshots

    # ------------------------------------------------------------------
    # 详情指标：两步 API 获取真实 Like/Collect 数
    # ------------------------------------------------------------------
    async def _fetch_detail_metrics(
        self, content_ids: List[str]
    ) -> Dict[str, Dict[str, int]]:
        """
        并发抓取每部剧的真实 Like（thumbUpNum）和 Collect（collectNum）。

        两步 API（均无需登录）：
          Step 1: /content/video/chapter/list?contentId={cid}&page=1&size=1
                  → 获取第一章节 ID
          Step 2: /content/video/chapter/behavior?contentId={cid}&chapterId={firstChapterId}
                  → 返回 {"thumbUpNum": "0.6M", "collectNum": "2.4M"}

        Returns:
            {content_id: {"like": int, "collect": int}}
        """
        results: Dict[str, Dict[str, int]] = {}
        sem = asyncio.Semaphore(_DETAIL_SEMAPHORE_SIZE)

        async with httpx.AsyncClient(
            headers=_API_HEADERS,
            follow_redirects=True,
            timeout=_DETAIL_TIMEOUT,
        ) as client:

            async def fetch_one(cid: str) -> None:
                async with sem:
                    try:
                        # Step 1: 取第一章节 ID
                        r1 = await client.get(
                            f"{_API_BASE}/content/video/chapter/list",
                            params={"contentId": cid, "page": 1, "size": 1},
                        )
                        d1 = r1.json()
                        if d1.get("code") != "00000":
                            return
                        records: list = (d1.get("data") or {}).get("records") or []
                        if not records:
                            return
                        first_chapter_id = records[0].get("id")
                        if not first_chapter_id:
                            return

                        # Step 2: 取章节行为数据（包含剧级别的 thumbUpNum / collectNum）
                        r2 = await client.get(
                            f"{_API_BASE}/content/video/chapter/behavior",
                            params={"contentId": cid, "chapterId": first_chapter_id},
                        )
                        d2 = r2.json()
                        if d2.get("code") != "00000":
                            return
                        behavior: dict = d2.get("data") or {}
                        like_val = _parse_metric_str(behavior.get("thumbUpNum"))
                        collect_val = _parse_metric_str(behavior.get("collectNum"))
                        if like_val > 0 or collect_val > 0:
                            results[cid] = {"like": like_val, "collect": collect_val}
                    except Exception as exc:
                        print(
                            f"[serealplus] _fetch_detail_metrics error "
                            f"for {cid}: {exc}"
                        )

            await asyncio.gather(*[fetch_one(cid) for cid in content_ids])

        return results

    # ------------------------------------------------------------------
    # fetch_snapshot 入口
    # ------------------------------------------------------------------
    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        html = await self.fetch_html(self.base_url, use_proxy=bool(self.proxy_pool))
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")

        # 找最大的 inline script（Nuxt 数据数组）
        large_scripts = [
            s for s in soup.find_all("script", src=False)
            if len(s.get_text()) > 5000
        ]
        if large_scripts:
            nuxt_script = max(large_scripts, key=lambda s: len(s.get_text()))
            content = nuxt_script.get_text().strip()
            try:
                arr = json.loads(content)
                if isinstance(arr, list) and len(arr) > 10:
                    snapshots = self._parse_nuxt_array(arr)
                    if snapshots:
                        # 并发抓取所有剧的真实 Like/Collect 数，覆盖位置估算值
                        content_ids = [s.external_id for s in snapshots if s.external_id]
                        metrics = await self._fetch_detail_metrics(content_ids)
                        for snap in snapshots:
                            m = metrics.get(snap.external_id)
                            if m:
                                snap.play_num = m.get("like", snap.play_num)
                                snap.collect_num = m.get("collect", snap.collect_num)
                        return snapshots
            except (json.JSONDecodeError, Exception):
                pass

        # 回退: 通用首页 HTML 解析（通常得不到封面）
        return await self.collect_homepage_snapshots(
            self.HOT_SECTION_TITLES,
            self.RISING_SECTION_TITLES,
            self.LINK_PATTERNS,
        )

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
