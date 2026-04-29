import aiosqlite
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from app.config import DATABASE_PATH
from app.models import DramaItem, DramaItemOut, DramaSnapshot


INIT_SQL = """
CREATE TABLE IF NOT EXISTS rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drama_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    tags TEXT,
    time_period TEXT NOT NULL,
    rank_type TEXT NOT NULL,
    rank_position INTEGER NOT NULL,
    score REAL,
    link TEXT,
    cover_url TEXT,
    play_num INTEGER,
    collect_num INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rankings_query
ON rankings(platform, rank_type, time_period, rank_position);

CREATE INDEX IF NOT EXISTS idx_rankings_updated
ON rankings(updated_at);

CREATE TABLE IF NOT EXISTS drama_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    drama_name TEXT NOT NULL,
    cover_url TEXT,
    link TEXT,
    tags TEXT,
    play_num INTEGER,
    collect_num INTEGER,
    extra_meta TEXT,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshots_platform_drama_time
ON drama_snapshots(platform, external_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_snapshots_recorded_at
ON drama_snapshots(recorded_at);
"""


TIME_PERIOD_WINDOWS = {
    "today": timedelta(hours=24),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
}


def _safe_log_score(value: float, ceiling: float) -> float:
    """对一个非负数值做 log 归一化为 0~10 的爆款评分"""
    if value <= 0 or ceiling <= 0:
        return 0.0
    score = math.log10(value + 1) / math.log10(ceiling + 1) * 10
    return round(max(0.0, min(10.0, score)), 2)


class Database:
    def __init__(self, db_path: str = str(DATABASE_PATH)):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(INIT_SQL)
            await self._migrate_rankings_metric_columns(db)
            await db.commit()

    async def _migrate_rankings_metric_columns(self, db: aiosqlite.Connection) -> None:
        """老库可能没有 play_num / collect_num 列，幂等添加"""
        async with db.execute("PRAGMA table_info(rankings)") as cursor:
            existing = {row[1] for row in await cursor.fetchall()}
        if "play_num" not in existing:
            await db.execute("ALTER TABLE rankings ADD COLUMN play_num INTEGER")
        if "collect_num" not in existing:
            await db.execute("ALTER TABLE rankings ADD COLUMN collect_num INTEGER")

    async def upsert_rankings(
        self,
        platform: str,
        rank_type: str,
        time_period: str,
        items: List[DramaItem]
    ) -> int:
        """插入或更新榜单数据，按平台+榜单类型+时间维度全量替换"""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            # 先删除该维度旧数据
            await db.execute(
                "DELETE FROM rankings WHERE platform=? AND rank_type=? AND time_period=?",
                (platform, rank_type, time_period)
            )
            # 插入新数据
            rows = [
                (
                    item.drama_name,
                    item.platform,
                    item.tags,
                    item.time_period,
                    item.rank_type,
                    item.rank_position,
                    item.score,
                    item.link,
                    item.cover_url,
                    item.play_num,
                    item.collect_num,
                    now,
                    now,
                )
                for item in items
            ]
            await db.executemany(
                """
                INSERT INTO rankings
                (drama_name, platform, tags, time_period, rank_type, rank_position,
                 score, link, cover_url, play_num, collect_num, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows
            )
            await db.commit()
            return len(rows)

    async def get_rankings(
        self,
        platform: Optional[str] = None,
        rank_type: Optional[str] = None,
        time_period: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[DramaItemOut], int]:
        """查询榜单数据，返回数据和总数"""
        conditions = []
        params = []
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        if rank_type:
            conditions.append("rank_type = ?")
            params.append(rank_type)
        if time_period:
            conditions.append("time_period = ?")
            params.append(time_period)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # 总数
            count_sql = f"SELECT COUNT(*) FROM rankings {where_clause}"
            async with db.execute(count_sql, params) as cursor:
                row = await cursor.fetchone()
                total = row[0] if row else 0

            # 数据
            data_sql = f"""
                SELECT * FROM rankings {where_clause}
                ORDER BY rank_position ASC
                LIMIT ? OFFSET ?
            """
            async with db.execute(data_sql, params + [limit, offset]) as cursor:
                rows = await cursor.fetchall()
                items = [DramaItemOut(**dict(row)) for row in rows]
                return items, total

    async def get_stats(self) -> List[dict]:
        """获取各平台数据统计"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT platform, rank_type, time_period, COUNT(*) as count, MAX(updated_at) as last_updated
                FROM rankings
                GROUP BY platform, rank_type, time_period
                ORDER BY platform, rank_type, time_period
                """
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_platforms(self) -> List[str]:
        """获取已抓取数据的平台列表"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT DISTINCT platform FROM rankings ORDER BY platform"
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def save_snapshots(
        self, platform: str, snapshots: List[DramaSnapshot], recorded_at: Optional[datetime] = None
    ) -> int:
        """批量写入一次抓取得到的剧集度量快照"""
        if not snapshots:
            return 0
        ts = (recorded_at or datetime.utcnow()).isoformat()
        rows = [
            (
                platform,
                snap.external_id,
                snap.drama_name,
                snap.cover_url,
                snap.link,
                snap.tags,
                snap.play_num,
                snap.collect_num,
                snap.extra_meta,
                ts,
            )
            for snap in snapshots
        ]
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                INSERT INTO drama_snapshots
                (platform, external_id, drama_name, cover_url, link, tags,
                 play_num, collect_num, extra_meta, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            await db.commit()
        return len(rows)

    async def _fetch_baseline_metrics(
        self,
        db: aiosqlite.Connection,
        platform: str,
        external_ids: List[str],
        before: datetime,
    ) -> Dict[str, Tuple[Optional[int], Optional[int]]]:
        """对每个 external_id，取早于 before 的最新快照，作为对比基线"""
        if not external_ids:
            return {}
        baseline: Dict[str, Tuple[Optional[int], Optional[int]]] = {}
        cutoff = before.isoformat()
        sql = """
            SELECT play_num, collect_num
            FROM drama_snapshots
            WHERE platform = ? AND external_id = ? AND recorded_at <= ?
            ORDER BY recorded_at DESC
            LIMIT 1
        """
        for ext_id in external_ids:
            async with db.execute(sql, (platform, ext_id, cutoff)) as cur:
                row = await cur.fetchone()
                if row:
                    baseline[ext_id] = (row[0], row[1])
        return baseline

    async def derive_rankings_from_snapshots(
        self,
        platform: str,
        snapshots: List[DramaSnapshot],
        rank_type: str,
        time_period: str,
        limit: int = 50,
        now: Optional[datetime] = None,
    ) -> List[DramaItem]:
        """
        基于当前快照与历史快照差值，派生今日/本周/本月榜单。
        - hot: 比对窗口内 play_num 的增量；窗口内无足够历史时回退到当前 play_num 排序
        - rising: 比对窗口内 collect_num 的增量；同样有回退
        - 评分使用本榜单内最高分做归一化
        """
        if not snapshots:
            return []

        now = now or datetime.utcnow()
        window = TIME_PERIOD_WINDOWS.get(time_period)
        if window is None:
            return []

        before = now - window
        external_ids = [snap.external_id for snap in snapshots if snap.external_id]

        async with aiosqlite.connect(self.db_path) as db:
            baseline = await self._fetch_baseline_metrics(
                db, platform, external_ids, before
            )

        valid_snapshots = [snap for snap in snapshots if snap.external_id]
        if not valid_snapshots:
            return []

        scored: List[Tuple[DramaSnapshot, float, float]] = []
        for snap in valid_snapshots:
            current_play = snap.play_num or 0
            current_collect = snap.collect_num or 0
            base_play, base_collect = baseline.get(snap.external_id, (None, None))

            if rank_type == "rising":
                if base_collect is not None and current_collect >= (base_collect or 0):
                    metric = current_collect - (base_collect or 0)
                else:
                    metric = current_collect
                fallback_metric = current_collect
            else:
                if base_play is not None and current_play >= (base_play or 0):
                    metric = current_play - (base_play or 0)
                else:
                    metric = current_play
                fallback_metric = current_play

            if metric <= 0:
                metric = fallback_metric

            scored.append((snap, float(metric), float(fallback_metric)))

        # 若该平台未提供 play/collect 等热度指标（全部为 0），用源端顺序派生位置分
        if all(metric <= 0 and fallback <= 0 for _, metric, fallback in scored):
            total = len(scored)
            scored = [
                (snap, float(total - idx), float(total - idx))
                for idx, (snap, _, _) in enumerate(scored)
            ]

        scored.sort(key=lambda item: (item[1], item[2]), reverse=True)
        scored = scored[:limit]
        if not scored:
            return []

        ceiling = max((m for _, m, _ in scored if m > 0), default=0)

        # 判断快照中的 play/collect 是否是平台真实指标。
        # NetShort 等没有真实数据的平台用合成位置分填充，数值范围一般 0~100，
        # 这里阈值取 1000 区分真实热度（最低也是数十万）和合成位置分。
        REAL_METRIC_THRESHOLD = 1000
        max_play = max((s.play_num or 0 for s in valid_snapshots), default=0)
        max_collect = max((s.collect_num or 0 for s in valid_snapshots), default=0)
        play_is_real = max_play >= REAL_METRIC_THRESHOLD
        collect_is_real = max_collect >= REAL_METRIC_THRESHOLD

        items: List[DramaItem] = []
        for idx, (snap, metric, _) in enumerate(scored, start=1):
            display_play = snap.play_num if (play_is_real and snap.play_num) else None
            display_collect = (
                snap.collect_num if (collect_is_real and snap.collect_num) else None
            )
            items.append(
                DramaItem(
                    drama_name=snap.drama_name,
                    platform=platform,
                    tags=snap.tags,
                    time_period=time_period,
                    rank_type=rank_type,
                    rank_position=idx,
                    score=_safe_log_score(metric, ceiling),
                    link=snap.link,
                    cover_url=snap.cover_url,
                    play_num=display_play,
                    collect_num=display_collect,
                )
            )
        return items

    async def get_cross_ranking(
        self,
        rank_type: str = "hot",
        time_period: str = "today",
        top_n: int = 20,
    ) -> list[dict]:
        """跨平台合并排名：按 play_num 降序取 Top N（仅含有真实播放量的记录）"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            sql = """
                SELECT drama_name, platform, play_num, collect_num, score,
                       rank_position, tags, link, cover_url
                FROM rankings
                WHERE rank_type = ? AND time_period = ?
                  AND play_num IS NOT NULL AND play_num > 0
                ORDER BY play_num DESC
                LIMIT ?
            """
            async with conn.execute(sql, (rank_type, time_period, top_n)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_platform_summary(
        self,
        rank_type: str = "hot",
        time_period: str = "today",
    ) -> list[dict]:
        """各平台播放量汇总统计（仅含有真实播放量的记录）"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            sql = """
                SELECT platform,
                       SUM(play_num) as total_play,
                       AVG(play_num) as avg_play,
                       MAX(play_num) as max_play,
                       COUNT(*) as drama_count
                FROM rankings
                WHERE rank_type = ? AND time_period = ?
                  AND play_num IS NOT NULL AND play_num > 0
                GROUP BY platform
                ORDER BY total_play DESC
            """
            async with conn.execute(sql, (rank_type, time_period)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        **dict(row),
                        "avg_play": round(row["avg_play"]) if row["avg_play"] else 0,
                    }
                    for row in rows
                ]

    async def cleanup_snapshots(self, days_to_keep: int = 45) -> int:
        """清理过老的快照，避免 SQLite 持续膨胀"""
        cutoff = (datetime.utcnow() - timedelta(days=days_to_keep)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "DELETE FROM drama_snapshots WHERE recorded_at < ?", (cutoff,)
            )
            await db.commit()
            return cur.rowcount or 0


db = Database()
