import csv
import io
from datetime import datetime
from typing import List, Optional

from app.database import Database
from app.models import DramaItemOut


class ExportService:
    """CSV导出服务"""

    def __init__(self, database: Database):
        self.db = database

    async def export_csv(
        self,
        platform: Optional[str] = None,
        rank_type: Optional[str] = None,
        time_period: Optional[str] = None,
    ) -> bytes:
        """导出CSV文件，返回字节流"""
        items, _ = await self.db.get_rankings(
            platform=platform,
            rank_type=rank_type,
            time_period=time_period,
            limit=10000,
            offset=0,
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow([
            "排名",
            "短剧名称",
            "来源平台",
            "标签",
            "时间周期",
            "榜单类型",
            "爆款评分",
            "跳转链接",
            "封面URL",
            "更新时间",
        ])

        # 写入数据
        for item in items:
            writer.writerow([
                item.rank_position,
                item.drama_name,
                item.platform,
                item.tags or "",
                item.time_period,
                item.rank_type,
                item.score if item.score is not None else "",
                item.link or "",
                item.cover_url or "",
                item.updated_at.isoformat() if item.updated_at else "",
            ])

        return output.getvalue().encode("utf-8-sig")

    def generate_filename(
        self,
        platform: Optional[str] = None,
        rank_type: Optional[str] = None,
        time_period: Optional[str] = None,
    ) -> str:
        """生成CSV文件名"""
        parts = ["drama_ranking"]
        if platform:
            parts.append(platform)
        if rank_type:
            parts.append(rank_type)
        if time_period:
            parts.append(time_period)
        parts.append(datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
        return "_".join(parts) + ".csv"
