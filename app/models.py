from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DramaItem(BaseModel):
    """短剧数据项"""
    drama_name: str = Field(..., description="短剧名称")
    platform: str = Field(..., description="来源平台")
    tags: Optional[str] = Field(None, description="标签")
    time_period: str = Field(..., description="时间周期: today/week/month")
    rank_type: str = Field(..., description="榜单类型: hot/rising")
    rank_position: int = Field(..., description="排名")
    score: Optional[float] = Field(None, description="爆款评分")
    link: Optional[str] = Field(None, description="跳转链接")
    cover_url: Optional[str] = Field(None, description="封面图URL")
    play_num: Optional[int] = Field(None, description="播放量")
    collect_num: Optional[int] = Field(None, description="收藏量")


class DramaSnapshot(BaseModel):
    """单个剧集的一次度量快照，用于派生今日/本周/本月榜单"""
    platform: str
    external_id: str
    drama_name: str
    cover_url: Optional[str] = None
    link: Optional[str] = None
    tags: Optional[str] = None
    play_num: Optional[int] = None
    collect_num: Optional[int] = None
    extra_meta: Optional[str] = None


class DramaItemOut(DramaItem):
    """带ID和时间戳的输出模型"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RankingQuery(BaseModel):
    """榜单查询参数"""
    platform: Optional[str] = None
    rank_type: Optional[str] = "hot"
    time_period: Optional[str] = "today"
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PlatformInfo(BaseModel):
    """平台信息"""
    key: str
    name: str
    base_url: str


class StatsItem(BaseModel):
    """统计项"""
    platform: str
    rank_type: str
    time_period: str
    count: int
    last_updated: Optional[datetime] = None
