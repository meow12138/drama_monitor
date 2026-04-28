import asyncio
import random
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import httpx
from playwright.async_api import async_playwright, Browser
from bs4 import BeautifulSoup

from app.config import (
    PROXY_POOL,
    USER_AGENT_POOL,
    REQUEST_TIMEOUT,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    MAX_RETRIES,
    RETRY_BACKOFF,
    FETCH_LIMIT,
)
from app.models import DramaItem, DramaSnapshot

# 模块级 Playwright 浏览器实例（复用）
_pw_instance = None
_pw_browser: Optional[Browser] = None


async def ensure_playwright_browser() -> Browser:
    """获取或创建全局 Playwright 浏览器实例"""
    global _pw_instance, _pw_browser
    if _pw_browser is None or _pw_browser.is_closed():
        _pw_instance = await async_playwright().start()
        _pw_browser = await _pw_instance.chromium.launch(headless=True)
    return _pw_browser


async def close_playwright_browser():
    """关闭全局 Playwright 浏览器实例"""
    global _pw_instance, _pw_browser
    if _pw_browser and not _pw_browser.is_closed():
        await _pw_browser.close()
        _pw_browser = None
    if _pw_instance:
        await _pw_instance.stop()
        _pw_instance = None


class BaseScraper(ABC):
    """爬虫基类，提供通用反爬、重试、抓取与解析能力"""

    platform_key: str = ""
    platform_name: str = ""
    base_url: str = ""
    API_ENDPOINTS: Dict[str, Dict[str, str]] = {}

    def __init__(self):
        self.proxy_pool = PROXY_POOL.copy()
        self.ua_pool = USER_AGENT_POOL.copy()
        self._client: Optional[httpx.AsyncClient] = None

    def _build_client(self, proxy: Optional[str] = None) -> httpx.AsyncClient:
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        return httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
            limits=limits,
            follow_redirects=True,
            proxy=proxy,
        )

    async def __aenter__(self):
        self._client = self._build_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _get_random_proxy(self) -> Optional[str]:
        if not self.proxy_pool:
            return None
        return random.choice(self.proxy_pool)

    def _get_random_ua(self) -> str:
        return random.choice(self.ua_pool)

    def _get_default_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self._get_random_ua(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    async def _delay(self):
        """随机延迟，降低请求频率"""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        await asyncio.sleep(delay)

    async def _http_get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_proxy: bool = True,
    ) -> Optional[httpx.Response]:
        """底层HTTP GET，带重试和代理轮换"""
        if not self._client:
            raise RuntimeError("Scraper must be used as async context manager")

        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)

        proxy = self._get_random_proxy() if use_proxy else None
        last_exception = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self._delay()
                if proxy:
                    async with self._build_client(proxy=proxy) as proxy_client:
                        response = await proxy_client.get(
                            url,
                            headers=request_headers,
                            params=params,
                        )
                else:
                    response = await self._client.get(
                        url,
                        headers=request_headers,
                        params=params,
                    )
                response.raise_for_status()
                return response
            except Exception as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    backoff = RETRY_BACKOFF ** attempt + random.uniform(0, 1)
                    await asyncio.sleep(backoff)
                    if use_proxy and self.proxy_pool:
                        proxy = self._get_random_proxy()

        print(f"[{self.platform_key}] HTTP GET failed for {url}: {last_exception}")
        return None

    async def fetch_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_proxy: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """发送HTTP GET请求，返回JSON数据"""
        resp = await self._http_get(url, headers, params, use_proxy)
        if resp is None:
            return None
        try:
            return resp.json()
        except Exception as e:
            print(f"[{self.platform_key}] JSON decode failed: {e}")
            return None

    async def fetch_html(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        use_proxy: bool = True,
    ) -> Optional[str]:
        """发送HTTP GET请求，返回HTML文本"""
        resp = await self._http_get(url, headers, None, use_proxy)
        if resp is None:
            return None
        return resp.text

    async def fetch_with_playwright(
        self,
        url: str,
        wait_selector: Optional[str] = None,
        wait_timeout: int = 10000,
    ) -> Optional[str]:
        """使用Playwright渲染页面，复用全局浏览器实例"""
        proxy = self._get_random_proxy()
        proxy_config = {"server": proxy} if proxy else None

        try:
            browser = await ensure_playwright_browser()
            context = await browser.new_context(
                user_agent=self._get_random_ua(),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                proxy=proxy_config,
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT * 1000)

            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=wait_timeout)
            else:
                await asyncio.sleep(2)

            content = await page.content()
            await context.close()
            return content
        except Exception as e:
            print(f"[{self.platform_key}] Playwright fetch failed for {url}: {e}")
            return None

    def _extract_list_from_response(self, data: Any) -> List[dict]:
        """从常见的API响应结构中提取列表"""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "result", "items", "list", "records", "content"):
                val = data.get(key)
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    for inner_key in ("list", "items", "data"):
                        inner_val = val.get(inner_key)
                        if isinstance(inner_val, list):
                            return inner_val
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []

    def _parse_item(self, raw: dict) -> Optional[DramaItem]:
        """从单个原始数据字典解析为DramaItem（字段名为常见模式）"""
        name = (
            raw.get("title")
            or raw.get("name")
            or raw.get("dramaName")
            or raw.get("drama_title")
            or ""
        )
        tags = raw.get("tags") or raw.get("category") or raw.get("genre") or raw.get("tag")
        if isinstance(tags, list):
            tags = ",".join(str(t) for t in tags)
        score = (
            raw.get("score")
            or raw.get("rating")
            or raw.get("hotScore")
            or raw.get("hot_score")
        )
        link = (
            raw.get("link")
            or raw.get("url")
            or raw.get("shareUrl")
            or raw.get("detailUrl")
            or raw.get("href")
        )
        cover = (
            raw.get("cover")
            or raw.get("coverUrl")
            or raw.get("thumbnail")
            or raw.get("coverImage")
            or raw.get("image")
        )

        try:
            score = float(score) if score is not None else None
        except (ValueError, TypeError):
            score = None

        if not name:
            return None
        return self._build_drama_item(
            drama_name=name,
            time_period="unknown",
            rank_type="unknown",
            rank_position=0,
            score=score,
            link=link,
            cover_url=cover,
            tags=tags,
        )

    async def fetch_ranking_via_api(
        self, url: str, time_period: str, rank_type: str
    ) -> List[DramaItem]:
        """通用API抓取与解析"""
        data = await self.fetch_json(url)
        if not data:
            return []

        raw_list = self._extract_list_from_response(data)
        items: List[DramaItem] = []
        for idx, raw in enumerate(raw_list[:FETCH_LIMIT], start=1):
            if not isinstance(raw, dict):
                continue
            item = self._parse_item(raw)
            if item:
                item.time_period = time_period
                item.rank_type = rank_type
                item.rank_position = idx
                items.append(item)
        return items

    async def fetch_ranking_via_html(
        self, url: str, time_period: str, rank_type: str
    ) -> List[DramaItem]:
        """通用HTML抓取与解析"""
        html = await self.fetch_html(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        selectors = [
            ".drama-item",
            ".rank-item",
            ".short-drama",
            "[data-rank]",
            ".content-item",
            ".item",
            ".drama-card",
            ".video-item",
            ".show-item",
        ]
        elements = []
        for sel in selectors:
            elements = soup.select(sel)
            if elements:
                break

        items: List[DramaItem] = []
        for idx, el in enumerate(elements[:FETCH_LIMIT], start=1):
            name_el = el.select_one(
                ".title, .name, h3, h4, .drama-title, .drama-name, [data-title]"
            )
            score_el = el.select_one(
                ".score, .rating, .hot-score, [data-score]"
            )
            link_el = el.select_one("a")
            cover_el = el.select_one("img")
            tags_el = el.select_one(
                ".tags, .category, .genre, [data-tags]"
            )

            name = name_el.get_text(strip=True) if name_el else ""
            score_text = score_el.get_text(strip=True) if score_el else None
            link = link_el.get("href") if link_el else None
            cover = cover_el.get("src") if cover_el else None
            tags = tags_el.get_text(strip=True) if tags_el else None

            try:
                score = float(re.sub(r"[^\d.]", "", score_text)) if score_text else None
            except (ValueError, TypeError):
                score = None

            if name:
                items.append(
                    self._build_drama_item(
                        drama_name=name,
                        time_period=time_period,
                        rank_type=rank_type,
                        rank_position=idx,
                        score=score,
                        link=link,
                        cover_url=cover,
                        tags=tags,
                    )
                )
        return items

    def _build_drama_item(
        self,
        drama_name: str,
        time_period: str,
        rank_type: str,
        rank_position: int,
        score: Optional[float] = None,
        link: Optional[str] = None,
        cover_url: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> DramaItem:
        """构建标准化的DramaItem"""
        if link and link.startswith("/"):
            link = self.base_url.rstrip("/") + link
        if cover_url and cover_url.startswith("/"):
            cover_url = self.base_url.rstrip("/") + cover_url

        return DramaItem(
            drama_name=drama_name.strip() if drama_name else "",
            platform=self.platform_key,
            tags=tags,
            time_period=time_period,
            rank_type=rank_type,
            rank_position=rank_position,
            score=score,
            link=link,
            cover_url=cover_url,
        )

    @abstractmethod
    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        """抓取近期热剧榜"""
        pass

    @abstractmethod
    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        """抓取新剧飙升榜"""
        pass

    async def fetch_all(self, time_period: str = "today") -> Dict[str, List[DramaItem]]:
        """抓取该平台的全部榜单"""
        return {
            "hot": await self.fetch_hot(time_period),
            "rising": await self.fetch_rising(time_period),
        }

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        """
        返回平台当前完整目录的度量快照（含 play_num / collect_num 等）。
        子类如能拿到真实的播放/收藏数据，应实现此方法。
        默认返回空列表，调度器会自动回退到 fetch_hot/fetch_rising 流程。
        """
        return []

    @property
    def supports_snapshot(self) -> bool:
        """子类实现 fetch_snapshot 时应将其设为 True"""
        return False

    # ---------- 通用首页卡片解析工具，供 SSR 站点子类复用 ----------

    def _find_section_root(
        self,
        heading_node,
        link_patterns: List[str],
        min_anchors: int = 4,
        max_levels: int = 6,
        min_imgs: int = 4,
    ):
        """
        从标题节点上溯找到包含分区卡片的容器：
        - 优先按 anchor 链接数量定位
        - 没有匹配 anchor 时，回退按 img 数量定位（覆盖纯图卡站点如 Sereal+）
        """
        current = heading_node
        anchor_root = None
        img_root = None
        for _ in range(max_levels):
            current = current.parent if current else None
            if current is None:
                break
            if anchor_root is None:
                anchors = current.find_all(
                    "a",
                    href=lambda h: bool(h) and any(p in h for p in link_patterns),
                )
                if len(anchors) >= min_anchors:
                    anchor_root = current
                    break
            if img_root is None:
                imgs_with_alt = [
                    img
                    for img in current.find_all("img")
                    if (img.get("alt") or "").strip()
                ]
                if len(imgs_with_alt) >= min_imgs:
                    img_root = current
        return anchor_root or img_root

    def _extract_id_from_href(self, href: str) -> Optional[str]:
        """从详情链接里粗略提取一个稳定的标识符"""
        if not href:
            return None
        # /drama/41000121776/Watch-Out-Im-The-Lady-Boss 形式
        match = re.search(r"/(\d{6,})(?:/|[-_])", href)
        if match:
            return match.group(1)
        match = re.search(r"-(\d{4,})(?:[/?]|$)", href)
        if match:
            return match.group(1)
        match = re.search(r"-([0-9a-f]{12,})(?:[/?]|$)", href, re.IGNORECASE)
        if match:
            return match.group(1)
        # fallback: 取最后一段路径
        path = href.split("?", 1)[0].rstrip("/")
        if path:
            return path.rsplit("/", 1)[-1]
        return None

    def _drama_name_from_href(self, href: str) -> str:
        """当 anchor 文本和 img alt 都没有有效剧名时，从 URL slug 还原一个名称"""
        if not href:
            return ""
        path = href.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        if not path:
            return ""
        # 取最后一段 slug
        last = path.rsplit("/", 1)[-1]
        # 去掉常见前后缀（episode-1-, -ID 等）
        last = re.sub(r"^(episode|ep|episodes)-\d+-", "", last, flags=re.IGNORECASE)
        last = re.sub(r"-\d{6,}$", "", last)
        last = re.sub(r"-[0-9a-f]{12,}$", "", last, flags=re.IGNORECASE)
        # 把 - / _ 转成空格
        from urllib.parse import unquote

        cleaned = unquote(last).replace("-", " ").replace("_", " ").strip()
        return cleaned

    def _resolve_image_url(self, img) -> Optional[str]:
        """从 <img> 节点尽量推断真实的封面 URL"""
        if img is None:
            return None

        def is_real(value: Optional[str]) -> bool:
            if not value:
                return False
            if value.startswith("data:image"):
                return False
            lower = value.lower()
            if any(
                marker in lower
                for marker in (
                    "placeholder",
                    "blank.gif",
                    "default-book-cover",
                    "default-cover",
                    "default_avatar",
                    "no-cover",
                    "no_cover",
                )
            ):
                return False
            return True

        for attr in ("data-src", "data-original", "src", "data-lazy-src"):
            value = img.get(attr)
            if is_real(value):
                return value
        srcset = img.get("srcset") or img.get("data-srcset") or ""
        if srcset:
            first = srcset.split(",")[0].strip().split(" ")[0]
            if is_real(first):
                return first
        return None

    def _slugify_name(self, name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
        return slug[:80] if slug else ""

    GENERIC_ANCHOR_TEXTS = {
        "watch now",
        "play",
        "play now",
        "view all",
        "see all",
        "see more",
        "more",
        "view more",
        "share",
        "like",
        "follow",
        "subscribe",
        "mute",
        "unmute",
        "next",
        "previous",
        "prev",
    }

    def _is_generic_action_text(self, text: str) -> bool:
        if not text:
            return False
        normalized = re.sub(r"[\s>›→\-_,.\u2192\u00bb]+", " ", text.lower()).strip()
        if normalized in self.GENERIC_ANCHOR_TEXTS:
            return True
        # "63 Episodes" / "Ep 12" / "12 eps" 这类角标
        if re.fullmatch(r"\d+\s*(episodes?|eps?|集)", normalized):
            return True
        if re.fullmatch(r"(ep|episode)\s*\d+", normalized):
            return True
        return False

    DEFAULT_TAG_LINK_PATTERNS = [
        "/genres/",
        "/genre/",
        "/tags/",
        "/tag/",
        "/category/",
        "/categories/",
        "/topic/",
        "/topics/",
        "/label/",
        "/labels/",
        "/themes/",
        "/theme/",
        "/shelf/",
    ]

    def _collect_tags_for_anchor(
        self,
        anchor,
        tag_patterns: List[str],
        max_anchors: int = 5,
        section_title_filters: Optional[List[str]] = None,
    ) -> List[str]:
        """从剧 anchor 的最近祖先容器内收集题材链接的文本"""
        if not tag_patterns:
            return []

        # 上溯到包含题材链接的最近祖先（最多 5 层）
        container = None
        current = anchor
        for _ in range(5):
            current = current.parent if current else None
            if current is None:
                break
            tag_anchors = current.find_all(
                "a",
                href=lambda h: bool(h) and any(p in h for p in tag_patterns),
            )
            if tag_anchors:
                container = current
                break
        if container is None:
            return []

        section_filter_norms = {
            t.strip().lower()
            for t in (section_title_filters or [])
            if t
        }

        tags: List[str] = []
        for tag_anchor in container.find_all(
            "a",
            href=lambda h: bool(h) and any(p in h for p in tag_patterns),
        ):
            # 跳过分区标题里的链接（h2/h3 内嵌的 anchor 是分区导航，不是 tag）
            if tag_anchor.find_parent(["h1", "h2", "h3", "h4"]) is not None:
                continue
            text = tag_anchor.get_text(" ", strip=True)
            if not text or self._is_generic_action_text(text):
                continue
            if text.strip().lower() in section_filter_norms:
                continue
            if text not in tags:
                tags.append(text)
            if len(tags) >= max_anchors:
                break
        return tags

    def _extract_drama_cards(
        self,
        section_root,
        link_patterns: List[str],
        skip_subtree=None,
        section_titles: Optional[List[str]] = None,
        tag_patterns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        在 section 容器内提取剧集卡片。
        - 优先以带剧集链接的 <a> 为锚点
        - 跳过 skip_subtree（通常是 section 标题节点）所属链接
        - 若没有可用的链接锚点，回退到 <img alt> 提取（覆盖 Sereal+ 这种无链接图卡）
        """
        if not section_root:
            return []

        heading_text_norm = ""
        if skip_subtree is not None:
            heading_text_norm = skip_subtree.get_text(" ", strip=True).strip().lower()
        all_heading_norms = set()
        if section_titles:
            all_heading_norms = {t.strip().lower() for t in section_titles if t}

        # 把 section root 内所有 h2/h3 节点全部纳入跳过列表
        # —— 它们的内嵌 anchor 都是分区标题链接，不应当作剧
        skip_subtrees = []
        if skip_subtree is not None:
            skip_subtrees.append(skip_subtree)
        for nested_heading in section_root.find_all(["h2", "h3"]):
            if skip_subtree is None or nested_heading is not skip_subtree:
                skip_subtrees.append(nested_heading)

        def is_skipped(node) -> bool:
            if not skip_subtrees:
                return False
            for sub in skip_subtrees:
                if node is sub:
                    return True
            for ancestor in node.parents:
                for sub in skip_subtrees:
                    if ancestor is sub:
                        return True
            return False

        def matches_heading(text: str) -> bool:
            if not text:
                return False
            normalized = text.strip().lower()
            if heading_text_norm and normalized == heading_text_norm:
                return True
            if normalized in all_heading_norms:
                return True
            return False

        cards: List[Dict[str, Any]] = []
        seen_ids = set()

        for anchor in section_root.find_all(
            "a",
            href=lambda h: bool(h) and any(p in h for p in link_patterns),
        ):
            if is_skipped(anchor):
                continue

            href = anchor.get("href") or ""
            external_id = self._extract_id_from_href(href)
            if not external_id or external_id in seen_ids:
                continue

            img = anchor.find("img")
            anchor_text = anchor.get_text(" ", strip=True)
            drama_name = ""
            cover_url: Optional[str] = None

            if img:
                drama_name = (img.get("alt") or "").strip()
                cover_url = self._resolve_image_url(img)

            # 部分站点（Melolo 等）把 <img> 放在 anchor 的兄弟/父级容器里
            if not cover_url:
                container = anchor.parent
                for _ in range(3):
                    if container is None:
                        break
                    sibling_img = container.find(
                        "img",
                        alt=lambda v: bool(v)
                        and (
                            v.strip().lower() == anchor_text.lower()
                            if anchor_text
                            else True
                        ),
                    )
                    if sibling_img is not None:
                        if not drama_name:
                            drama_name = (sibling_img.get("alt") or "").strip()
                        cover_url = self._resolve_image_url(sibling_img)
                        if cover_url:
                            break
                    container = container.parent

            if not drama_name and anchor_text and not self._is_generic_action_text(anchor_text):
                drama_name = anchor_text

            if not drama_name or self._is_generic_action_text(drama_name):
                parent = anchor.parent
                title_el = (
                    parent.select_one(".title, .name, h2, h3, h4")
                    if parent
                    else None
                )
                if title_el:
                    title_text = title_el.get_text(" ", strip=True)
                    if title_text and not self._is_generic_action_text(title_text):
                        drama_name = title_text

            # 仍然没有像样剧名时，尝试从 URL slug 还原（适配 DramaBox 这种封面 anchor 没 alt 的情况）
            if not drama_name or self._is_generic_action_text(drama_name):
                slug_name = self._drama_name_from_href(href)
                if slug_name:
                    drama_name = slug_name

            # 过滤掉 "Watch Now"/"View all"/"63 Episodes" 这类按钮 anchor
            if self._is_generic_action_text(drama_name):
                continue
            # 过滤掉与分区标题同名的 anchor（FlexTV 等站点的标题链接）
            if matches_heading(drama_name):
                continue

            if not cover_url:
                noscript = anchor.find("noscript")
                if noscript:
                    # 浏览器禁 JS 时 noscript 内容会渲染，bs4 也按 HTML 解析其子节点
                    inner_img = noscript.find("img")
                    if inner_img is None:
                        # 部分服务端会把 noscript 内容当作字符串存放，需要再解析一次
                        inner_img = BeautifulSoup(
                            noscript.decode_contents(), "html.parser"
                        ).find("img")
                    if inner_img is not None:
                        cover_url = self._resolve_image_url(inner_img)

            drama_name = (drama_name or "").strip()
            if not drama_name:
                continue

            tags = self._collect_tags_for_anchor(
                anchor,
                tag_patterns or [],
                section_title_filters=section_titles,
            )
            seen_ids.add(external_id)
            cards.append(
                {
                    "external_id": external_id,
                    "drama_name": drama_name,
                    "cover_url": cover_url,
                    "link": self._absolute_url(href),
                    "tags": tags,
                }
            )

        if cards:
            return cards

        # 回退：站点没有真实 anchor 卡片，但 SSR 仍会渲染带 alt 的封面图
        for img in section_root.find_all("img"):
            if is_skipped(img):
                continue
            alt = (img.get("alt") or "").strip()
            if not alt:
                continue
            # 跳过页面上 Like/Share/Play/Mute 这类装饰按钮的 alt
            if self._is_generic_action_text(alt):
                continue
            if matches_heading(alt):
                continue
            slug = self._slugify_name(alt)
            if not slug or slug in seen_ids:
                continue
            cover_url = self._resolve_image_url(img)
            if not cover_url:
                noscript = img.find_parent("noscript") or img.find_next("noscript")
                if noscript:
                    inner_img = noscript.find("img")
                    if inner_img is None:
                        inner_img = BeautifulSoup(
                            noscript.decode_contents(), "html.parser"
                        ).find("img")
                    if inner_img is not None:
                        cover_url = self._resolve_image_url(inner_img)
            tags = self._collect_tags_for_anchor(
                img,
                tag_patterns or [],
                section_title_filters=section_titles,
            )
            seen_ids.add(slug)
            cards.append(
                {
                    "external_id": slug,
                    "drama_name": alt,
                    "cover_url": cover_url,
                    "link": None,
                    "tags": tags,
                }
            )
        return cards

    def _absolute_url(self, href: Optional[str]) -> Optional[str]:
        if not href:
            return None
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"{self.base_url.rstrip('/')}{href}"
        return f"{self.base_url.rstrip('/')}/{href}"

    def _find_section_by_title(
        self, soup: BeautifulSoup, title: str
    ):
        """模糊匹配 h2/h3 标题：去掉 emoji 等装饰字符后比对开头"""
        title_norm = title.strip().lower()

        def matches(text: str) -> bool:
            text_clean = text.strip().lower()
            return text_clean == title_norm or text_clean.startswith(title_norm)

        for tag in soup.find_all(["h2", "h3"]):
            text = tag.get_text(" ", strip=True)
            if matches(text):
                return tag
            link = tag.find("a")
            if link and matches(link.get_text(" ", strip=True)):
                return tag
        return None

    def _collect_section_cards(
        self,
        soup: BeautifulSoup,
        title_keywords: List[str],
        link_patterns: List[str],
        tag_patterns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        聚合 soup 内所有标题命中 title_keywords 的分区卡片，按出现顺序去重合并。
        title_keywords 为大小写无关的子串/前缀。
        """
        if not title_keywords:
            return []
        keywords_lower = [t.strip().lower() for t in title_keywords if t]

        def title_matches(text: str) -> bool:
            text_clean = text.strip().lower()
            return any(
                text_clean == k or text_clean.startswith(k) or k in text_clean
                for k in keywords_lower
            )

        merged: List[Dict[str, Any]] = []
        seen_ids = set()

        # 收集本次匹配到的分区标题（仅用于跨分区互过滤，避免把另一个分区的标题
        # 误识别为剧名；不能用全量 h2 文本，因为部分站点把剧名也写成 h2）。
        section_title_filters: List[str] = []
        for heading in soup.find_all(["h2", "h3"]):
            text = heading.get_text(" ", strip=True)
            anchor_in_heading = heading.find("a")
            anchor_text = (
                anchor_in_heading.get_text(" ", strip=True) if anchor_in_heading else ""
            )
            if title_matches(text) or title_matches(anchor_text):
                if text:
                    section_title_filters.append(text)
                if anchor_text and anchor_text != text:
                    section_title_filters.append(anchor_text)

        for heading in soup.find_all(["h2", "h3"]):
            text = heading.get_text(" ", strip=True)
            anchor_in_heading = heading.find("a")
            anchor_text = (
                anchor_in_heading.get_text(" ", strip=True) if anchor_in_heading else ""
            )
            if not (title_matches(text) or title_matches(anchor_text)):
                continue

            root = self._find_section_root(heading, link_patterns)
            if not root and heading.parent is not None:
                root = heading.parent.parent or heading.parent
            cards = self._extract_drama_cards(
                root,
                link_patterns,
                skip_subtree=heading,
                section_titles=section_title_filters,
                tag_patterns=tag_patterns,
            )
            for card in cards:
                if card["external_id"] in seen_ids:
                    continue
                seen_ids.add(card["external_id"])
                merged.append(card)
        return merged

    async def collect_homepage_snapshots(
        self,
        hot_section_titles: List[str],
        rising_section_titles: List[str],
        link_patterns: List[str],
        tag_patterns: Optional[List[str]] = None,
    ) -> List[DramaSnapshot]:
        """
        通用 SSR 首页快照采集：
        - 聚合所有命中 hot_section_titles 的分区卡片，位置反推 play_num
        - 聚合所有命中 rising_section_titles 的分区卡片，位置反推 collect_num
        - 同一剧出现在多分区时，play_num/collect_num 取该列表中最高位置分
        """
        html = await self.fetch_html(self.base_url, use_proxy=bool(self.proxy_pool))
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        effective_tag_patterns = (
            tag_patterns if tag_patterns is not None else self.DEFAULT_TAG_LINK_PATTERNS
        )

        hot_cards = self._collect_section_cards(
            soup, hot_section_titles, link_patterns, effective_tag_patterns
        )
        rising_cards = self._collect_section_cards(
            soup, rising_section_titles, link_patterns, effective_tag_patterns
        )

        # 单边为空时，让另一边的数据双向使用，保证至少有快照
        if not hot_cards and rising_cards:
            hot_cards = list(rising_cards)
        if not rising_cards and hot_cards:
            rising_cards = list(hot_cards)

        merged: Dict[str, Dict[str, Any]] = {}
        hot_count = len(hot_cards)
        rising_count = len(rising_cards)

        def merge_tags(entry: Dict[str, Any], new_tags: List[str]) -> None:
            existing = entry.get("tags") or []
            if not isinstance(existing, list):
                existing = [existing]
            for tag in new_tags or []:
                if tag and tag not in existing:
                    existing.append(tag)
            entry["tags"] = existing

        for idx, card in enumerate(hot_cards):
            entry = merged.setdefault(card["external_id"], dict(card))
            entry["play_num_synth"] = max(
                entry.get("play_num_synth", 0), max(0, hot_count - idx)
            )
            entry.setdefault("collect_num_synth", 0)
            merge_tags(entry, card.get("tags") or [])

        for idx, card in enumerate(rising_cards):
            entry = merged.setdefault(card["external_id"], dict(card))
            entry["collect_num_synth"] = max(
                entry.get("collect_num_synth", 0), max(0, rising_count - idx)
            )
            entry.setdefault("play_num_synth", 0)
            merge_tags(entry, card.get("tags") or [])

        snapshots: List[DramaSnapshot] = []
        for entry in merged.values():
            tag_list = entry.get("tags") or []
            tags_value = ", ".join(tag_list) if tag_list else None
            snapshots.append(
                DramaSnapshot(
                    platform=self.platform_key,
                    external_id=entry["external_id"],
                    drama_name=entry["drama_name"],
                    cover_url=entry.get("cover_url"),
                    link=entry.get("link"),
                    tags=tags_value,
                    play_num=int(entry.get("play_num_synth", 0)),
                    collect_num=int(entry.get("collect_num_synth", 0)),
                )
            )
        return snapshots
