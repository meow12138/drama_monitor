"""
MoboReels 爬虫
官网: https://www.moboreels.com（实际归属 minidrama.com / 畅读科技）

实现说明:
1. 该站为 Nuxt SSR，window.__NUXT__ 被压缩为 IIFE 形式（参数引用）。
2. 内部 API 域名 videoapi-hk.cdreader.com 在当前网络下不可达，因此走主页 SSR 数据。
3. 使用 Node 子进程把 IIFE 求值出来，得到 state.recList 与 state.hotWord。
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

from app.config import FETCH_LIMIT
from app.models import DramaItem, DramaSnapshot
from app.scrapers.base import BaseScraper


class MoboReelsScraper(BaseScraper):
    platform_key = "moboreels"
    platform_name = "MoboReels"
    base_url = "https://www.moboreels.com"

    NUXT_TIMEOUT_SECONDS = 15

    @property
    def supports_snapshot(self) -> bool:
        return True

    async def _fetch_nuxt_payload(self) -> Optional[Dict[str, Any]]:
        html = await self.fetch_html(self.base_url, use_proxy=bool(self.proxy_pool))
        if not html:
            return None

        marker = "window.__NUXT__="
        start = html.find(marker)
        if start == -1:
            return None

        end = html.find("</script>", start)
        if end == -1:
            return None

        snippet = html[start + len(marker) : end].strip().rstrip(";").strip()
        if not snippet:
            return None

        return await self._eval_nuxt_via_node(snippet)

    def _run_node_blocking(self, tmp_path: str) -> Optional[Dict[str, Any]]:
        # 在线程池中同步执行 node，兼容 Windows SelectorEventLoop
        try:
            result = subprocess.run(
                ["node", tmp_path],
                capture_output=True,
                timeout=self.NUXT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            print(f"[{self.platform_key}] NUXT eval timeout")
            return None
        except FileNotFoundError:
            print(
                f"[{self.platform_key}] node executable not found; "
                "MoboReels scraper requires Node.js on PATH"
            )
            return None

        if result.returncode != 0:
            print(
                f"[{self.platform_key}] NUXT eval failed: {result.stderr.decode('utf-8', errors='replace')[:300]}"
            )
            return None

        try:
            return json.loads(result.stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            print(f"[{self.platform_key}] NUXT JSON decode failed: {exc}")
            return None

    async def _eval_nuxt_via_node(self, snippet: str) -> Optional[Dict[str, Any]]:
        # 写到临时 JS 文件再让 Node 求值，避免 Windows 命令行长度限制
        wrapped = f"process.stdout.write(JSON.stringify({snippet}));"

        tmp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".js",
                delete=False,
                encoding="utf-8",
            ) as fh:
                fh.write(wrapped)
                tmp_path = fh.name

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._run_node_blocking, tmp_path)
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _build_drama_url(self, series_name: Optional[str], series_id: Optional[str] = None) -> Optional[str]:
        if not series_name:
            return None
        slug = re.sub(r"[^a-z0-9\s-]", "", series_name.lower())
        slug = re.sub(r"[\s]+", "-", slug.strip())
        slug = re.sub(r"-+", "-", slug).strip("-")
        if not slug:
            return None
        if series_id:
            return f"{self.base_url.rstrip('/')}/drama/{slug}-{series_id}"
        return f"{self.base_url.rstrip('/')}/search/{slug}"

    def _normalize_tags(self, raw: Dict[str, Any]) -> Optional[str]:
        types = raw.get("types")
        if isinstance(types, list) and types:
            return ", ".join(str(t) for t in types if t)
        type_items = raw.get("typeItemVOList") or []
        names = [item.get("typeName") for item in type_items if item.get("typeName")]
        if names:
            return ", ".join(str(n) for n in names)
        return None

    def _build_snapshots_from_payload(
        self, payload: Dict[str, Any]
    ) -> List[DramaSnapshot]:
        state = payload.get("state") or {}
        rec_list = state.get("recList") or []

        snapshots: List[DramaSnapshot] = []
        seen_ids = set()
        for raw in rec_list[:FETCH_LIMIT]:
            series_id = raw.get("seriesId")
            series_name = raw.get("seriesName") or raw.get("name")
            if not series_id or not series_name:
                continue
            if series_id in seen_ids:
                continue
            seen_ids.add(series_id)

            cover_url = raw.get("coverUrl") or raw.get("appBannerUrl")
            link = self._build_drama_url(series_name, str(series_id))
            tags = self._normalize_tags(raw)

            extra_meta = json.dumps(
                {
                    "lastEpis": raw.get("lastEpis"),
                    "allEpis": raw.get("allEpis"),
                    "ending": raw.get("ending"),
                },
                ensure_ascii=False,
            )

            snapshots.append(
                DramaSnapshot(
                    platform=self.platform_key,
                    external_id=str(series_id),
                    drama_name=series_name,
                    cover_url=cover_url,
                    link=link,
                    tags=tags,
                    play_num=None,
                    collect_num=None,
                    extra_meta=extra_meta,
                )
            )
        return snapshots

    async def fetch_snapshot(self) -> List[DramaSnapshot]:
        payload = await self._fetch_nuxt_payload()
        if not payload:
            return []
        return self._build_snapshots_from_payload(payload)

    async def fetch_hot(self, time_period: str = "today") -> List[DramaItem]:
        # 调度器会优先走 snapshot 路径；保留此方法以兼容旧调用
        return []

    async def fetch_rising(self, time_period: str = "today") -> List[DramaItem]:
        return []
