import asyncio
import json
import math
import re
import time
from base64 import b64decode, b64encode
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from app.config import FETCH_LIMIT, MAX_RETRIES, RETRY_BACKOFF
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper


class ShortMaxScraper(BaseScraper):
    """
    ShortMax 爬虫
    官网: https://www.shorttv.live
    """
    platform_key = "shortmax"
    platform_name = "ShortMax"
    base_url = "https://www.shorttv.live"

    SECTION_TITLES = {
        "hot": "Most Popular",
        "rising": "New Release",
    }
    API_BASE_URL = "https://shortweb.shorttv.live/app-api/app"
    API_SECRET_KEY = "shortwebapiaesen".encode("utf-8")
    API_HEADERS = {
        "Content-Type": "application/json",
        "X-Encrypted": "true",
        "Language-Code": "en",
    }
    API_PAGE_SIZE = max(FETCH_LIMIT, 50)
    API_SAMPLE_PAGES = max(2, math.ceil((FETCH_LIMIT * 2) / API_PAGE_SIZE))
    TAG_INDEX_TTL_SECONDS = 6 * 3600  # 题材索引缓存 6 小时

    _shared_tag_index: Optional[Dict[str, List[str]]] = None
    _shared_tag_index_at: float = 0.0

    def __init__(self):
        super().__init__()
        self._catalog_cache: Optional[List[Dict[str, Any]]] = None
        self._tag_index: Optional[Dict[str, List[str]]] = None

    def _build_shortmax_link(self, raw: Dict[str, Any]) -> Optional[str]:
        short_play_id = raw.get("shortPlayId")
        raw_name = raw.get("rawName") or raw.get("shortPlayName") or raw.get("lanShortPlayName")
        if not short_play_id or not raw_name:
            return None
        return f"/drama/{self._to_slug(raw_name)}-{short_play_id}"

    def _to_slug(self, text: str) -> str:
        cleaned = re.sub(
            r"""[？！!"#$%&'()*+,./:;<=>?@[\\\]^_`{|}~、。「」『』《》〈〉———…～·￥【】（）：・ー※]""",
            "",
            text,
        ).strip()
        replaced = re.sub(r"\s+", "-", cleaned).lower()
        return quote(replaced, safe="")

    def _build_tags(self, raw: Dict[str, Any], drama_tags: Optional[List[str]] = None) -> Optional[str]:
        if drama_tags:
            return ", ".join(drama_tags)
        tags: List[str] = []
        if raw.get("convertPlayNum"):
            tags.append(f"Play {raw['convertPlayNum']}")
        if raw.get("convertCollectNum"):
            tags.append(f"Collect {raw['convertCollectNum']}")
        return ", ".join(tags) if tags else None

    async def _build_tag_index(self) -> Dict[str, List[str]]:
        """以 cmsClassNew/queryList 中的题材分类作为标签来源，反推 drama_id -> 题材列表

        说明: 反推索引耗时较长（~3 分钟），通过类级缓存 + TTL 共享给同进程内所有实例，
        避免每个抓取周期都重新构建。
        """
        if self._tag_index is not None:
            return self._tag_index

        now = time.monotonic()
        if (
            ShortMaxScraper._shared_tag_index is not None
            and now - ShortMaxScraper._shared_tag_index_at < self.TAG_INDEX_TTL_SECONDS
        ):
            self._tag_index = ShortMaxScraper._shared_tag_index
            return self._tag_index

        classes_resp = await self._post_encrypted("/cmsClassNew/queryList", {})
        classes = ((classes_resp or {}).get("data")) or []

        drama_to_tags: Dict[str, List[str]] = {}
        seen_class_ids = set()
        for cls in classes:
            class_id = cls.get("classId")
            if not class_id or class_id in seen_class_ids:
                continue
            seen_class_ids.add(class_id)
            display_name = (
                cls.get("displayName") or cls.get("rawName") or cls.get("className")
            )
            if not display_name:
                continue

            for page_no in (1, 2):
                resp = await self._post_encrypted(
                    "/cmsShortPlay/queryPage",
                    {
                        "pageNo": page_no,
                        "pageSize": 100,
                        "labelId": "",
                        "classId": class_id,
                    },
                )
                items = ((resp or {}).get("data") or {}).get("list") or []
                if not items:
                    break
                for raw in items:
                    spid = str(raw.get("shortPlayId") or "")
                    if not spid:
                        continue
                    bucket = drama_to_tags.setdefault(spid, [])
                    if display_name not in bucket:
                        bucket.append(display_name)
                if len(items) < 100:
                    break

        ShortMaxScraper._shared_tag_index = drama_to_tags
        ShortMaxScraper._shared_tag_index_at = time.monotonic()
        self._tag_index = drama_to_tags
        return drama_to_tags

    def _encrypt_payload(self, payload: Dict[str, Any]) -> bytes:
        plain_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        cipher = AES.new(self.API_SECRET_KEY, AES.MODE_CBC, iv=self.API_SECRET_KEY)
        return b64encode(cipher.encrypt(pad(plain_text, AES.block_size)))

    def _decrypt_response(self, encrypted_text: str) -> Dict[str, Any]:
        cipher = AES.new(self.API_SECRET_KEY, AES.MODE_CBC, iv=self.API_SECRET_KEY)
        decrypted = unpad(cipher.decrypt(b64decode(encrypted_text.strip())), AES.block_size)
        return json.loads(decrypted.decode("utf-8"))

    async def _post_encrypted(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._client:
            raise RuntimeError("Scraper must be used as async context manager")

        url = f"{self.API_BASE_URL}{path}"
        body = self._encrypt_payload(payload)
        proxy = self._get_random_proxy()
        last_exception: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self._delay()
                if proxy:
                    async with self._build_client(proxy=proxy) as proxy_client:
                        response = await proxy_client.post(
                            url,
                            headers=self.API_HEADERS,
                            content=body,
                        )
                else:
                    response = await self._client.post(
                        url,
                        headers=self.API_HEADERS,
                        content=body,
                    )
                response.raise_for_status()
                return self._decrypt_response(response.text)
            except Exception as exc:
                last_exception = exc
                if attempt < MAX_RETRIES:
                    backoff = RETRY_BACKOFF ** attempt
                    if self.proxy_pool:
                        proxy = self._get_random_proxy()
                    await asyncio.sleep(backoff)

        print(f"[{self.platform_key}] Encrypted POST failed for {url}: {last_exception}")
        return None

    async def _load_catalog(self) -> List[Dict[str, Any]]:
        if self._catalog_cache is not None:
            return self._catalog_cache

        unique_items: Dict[Any, Dict[str, Any]] = {}
        for page_no in range(1, self.API_SAMPLE_PAGES + 1):
            response = await self._post_encrypted(
                "/cmsShortPlay/queryPage",
                {
                    "pageNo": page_no,
                    "pageSize": self.API_PAGE_SIZE,
                    "labelId": "",
                    "classId": "",
                },
            )
            page_data = response.get("data", {}) if response else {}
            page_items = page_data.get("list") or []
            if not page_items:
                break
            for item in page_items:
                short_play_id = item.get("shortPlayId")
                if short_play_id and short_play_id not in unique_items:
                    unique_items[short_play_id] = item

            total = page_data.get("total") or 0
            if total and len(unique_items) >= total:
                break

        self._catalog_cache = list(unique_items.values())
        return self._catalog_cache

    def _build_items_from_catalog(
        self,
        catalog: List[Dict[str, Any]],
        time_period: str,
        rank_type: str,
        sort_mode: str,
    ) -> List[DramaItem]:
        if sort_mode == "play_desc":
            ordered = sorted(
                catalog,
                key=lambda item: (
                    item.get("playNum") or 0,
                    item.get("collectNum") or 0,
                    item.get("shortPlayId") or 0,
                ),
                reverse=True,
            )
        else:
            ordered = list(catalog)

        items: List[DramaItem] = []
        for idx, raw in enumerate(ordered[:FETCH_LIMIT], start=1):
            drama_name = raw.get("lanShortPlayName") or raw.get("shortPlayName") or raw.get("rawName")
            if not drama_name:
                continue

            items.append(
                self._build_drama_item(
                    drama_name=drama_name,
                    time_period=time_period,
                    rank_type=rank_type,
                    rank_position=idx,
                    score=None,
                    link=self._build_shortmax_link(raw),
                    cover_url=raw.get("lanCoverId") or raw.get("coverId") or raw.get("horizontalCoverId"),
                    tags=self._build_tags(raw),
                )
            )
        return items

    async def _fetch_home_section(
        self, section_title: str, time_period: str, rank_type: str
    ) -> List[DramaItem]:
        """
        ShortMax 首页已服务端渲染剧集卡片，但未公开稳定的榜单 API。
        先复用首页的公开分区作为可落库的数据源。
        """
        html = await self.fetch_html(self.base_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find(
            lambda tag: tag.name == "h2"
            and tag.get_text(" ", strip=True).startswith(section_title)
        )
        if not heading:
            print(f"[{self.platform_key}] Section not found: {section_title}")
            return []

        section = heading.find_parent("section")
        if not section:
            print(f"[{self.platform_key}] Section wrapper missing: {section_title}")
            return []

        items: List[DramaItem] = []
        cards = section.select("div.drama-card")
        for idx, card in enumerate(cards[:FETCH_LIMIT], start=1):
            image_link = card.select_one("a.card-image")
            title_link = card.select_one("a.card-title-layout")
            image = image_link.select_one("img") if image_link else None

            drama_name = ""
            if title_link:
                drama_name = title_link.get_text(" ", strip=True)
            if not drama_name and image:
                drama_name = image.get("alt", "").strip()
            if not drama_name:
                continue

            detail_link = title_link.get("href") if title_link else None
            play_link = image_link.get("href") if image_link else None
            link = detail_link or play_link
            cover_url = image.get("data-src") or image.get("src") if image else None

            items.append(
                self._build_drama_item(
                    drama_name=drama_name,
                    time_period=time_period,
                    rank_type=rank_type,
                    rank_position=idx,
                    score=None,
                    link=link,
                    cover_url=cover_url,
                    tags=section_title,
                )
            )

        return items

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        catalog = await self._load_catalog()
        if catalog:
            return self._build_items_from_catalog(
                catalog,
                time_period=time_period,
                rank_type="hot",
                sort_mode="play_desc",
            )
        return await self._fetch_home_section(self.SECTION_TITLES["hot"], time_period, "hot")

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        catalog = await self._load_catalog()
        if catalog:
            return self._build_items_from_catalog(
                catalog,
                time_period=time_period,
                rank_type="rising",
                sort_mode="api_order",
            )
        return await self._fetch_home_section(self.SECTION_TITLES["rising"], time_period, "rising")

    @property
    def supports_snapshot(self) -> bool:
        return True

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        """以 cmsShortPlay/queryPage 的全量分页结果作为度量快照"""
        catalog = await self._load_catalog()
        try:
            tag_index = await self._build_tag_index()
        except Exception as exc:
            print(f"[{self.platform_key}] Tag index unavailable: {exc}")
            tag_index = {}

        snapshots: List[DramaSnapshot] = []
        for raw in catalog:
            short_play_id = raw.get("shortPlayId")
            drama_name = (
                raw.get("lanShortPlayName")
                or raw.get("shortPlayName")
                or raw.get("rawName")
            )
            if not short_play_id or not drama_name:
                continue

            link_path = self._build_shortmax_link(raw)
            link = (
                f"{self.base_url.rstrip('/')}{link_path}"
                if link_path and link_path.startswith("/")
                else link_path
            )
            cover_url = (
                raw.get("lanCoverId")
                or raw.get("coverId")
                or raw.get("horizontalCoverId")
            )
            tag_names = tag_index.get(str(short_play_id))
            snapshots.append(
                DramaSnapshot(
                    platform=self.platform_key,
                    external_id=str(short_play_id),
                    drama_name=drama_name,
                    cover_url=cover_url,
                    link=link,
                    tags=self._build_tags(raw, drama_tags=tag_names),
                    play_num=raw.get("playNum") or 0,
                    collect_num=raw.get("collectNum") or 0,
                )
            )
        return snapshots
