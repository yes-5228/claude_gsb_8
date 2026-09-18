"""群众诉求受理相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ComplaintCategory,
    ComplaintSource,
    FollowUpResult,
    FollowUpSatisfaction,
)
from app.schemas.restroom import RestroomBrief


class ComplaintFlowRecordOut(BaseModel):
    """办理流水节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    from_status: str
    to_status: str
    operator: str
    remark: str | None = None
    created_at: datetime


class FollowUpRecordOut(BaseModel):
    """一次回访记录。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    result: str
    satisfaction: str | None = None
    operator: str
    remark: str | None = None
    created_at: datetime


class ComplaintBase(BaseModel):
    source: ComplaintSource = Field(default=ComplaintSource.PUBLIC, description="诉求来源")
    content: str = Field(min_length=1, max_length=1000, description="反映内容")
    category: ComplaintCategory | None = Field(
        default=None, description="诉求分类，留空按内容自动判定"
    )
    reporter_name: str = Field(default="", max_length=60, description="反映人姓名，可匿名")
    reporter_phone: str = Field(min_length=1, max_length=30, description="联系电话，用于回访")
    receiver: str = Field(default="", max_length=60, description="受理人")


class ComplaintCreate(ComplaintBase):
    restroom_id: int = Field(description="涉及公厕")
    received_at: datetime | None = Field(default=None, description="受理时间，留空取当前时间")
    initial_remark: str | None = Field(default=None, max_length=500, description="受理备注")


class ComplaintUpdate(BaseModel):
    """登记信息补正；内容变更且未指定分类时会重新自动判定。"""

    source: ComplaintSource | None = None
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    category: ComplaintCategory | None = None
    reporter_name: str | None = Field(default=None, max_length=60)
    reporter_phone: str | None = Field(default=None, min_length=1, max_length=30)
    receiver: str | None = Field(default=None, max_length=60)


class ComplaintAssign(BaseModel):
    """分派（或改派）处理人。"""

    handler: str = Field(min_length=1, max_length=60, description="处理人")
    operator: str = Field(min_length=1, max_length=60, description="操作人")
    remark: str | None = Field(default=None, max_length=500, description="分派说明")


class ComplaintFinish(BaseModel):
    """处理完成，登记处理结果。"""

    result: str = Field(min_length=1, max_length=500, description="处理结果")
    operator: str = Field(min_length=1, max_length=60, description="操作人")
    remark: str | None = Field(default=None, max_length=500, description="补充说明")


class FollowUpCreate(BaseModel):
    """登记一次回访；未联系上时必须约定下次回访时间。"""

    result: FollowUpResult = Field(description="回访结果")
    satisfaction: FollowUpSatisfaction | None = Field(default=None, description="满意度")
    next_follow_time: datetime | None = Field(
        default=None, description="下次回访时间，未联系上时必填"
    )
    operator: str = Field(min_length=1, max_length=60, description="回访人")
    remark: str | None = Field(default=None, max_length=500, description="回访备注")


class ComplaintClose(BaseModel):
    """作废关闭。"""

    operator: str = Field(min_length=1, max_length=60, description="操作人")
    remark: str | None = Field(default=None, max_length=500, description="关闭原因")


class ClassifyPreview(BaseModel):
    content: str = Field(min_length=1, max_length=1000, description="反映内容")


class ClassifyResult(BaseModel):
    category: str


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    restroom_id: int
    restroom: RestroomBrief | None = None
    source: str
    content: str
    category: str
    status: str
    reporter_name: str
    reporter_phone: str
    receiver: str
    handler: str
    result: str
    received_at: datetime
    assigned_at: datetime | None = None
    finished_at: datetime | None = None
    next_follow_time: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    records: list[ComplaintFlowRecordOut] = Field(default_factory=list)
    follow_ups: list[FollowUpRecordOut] = Field(default_factory=list)
