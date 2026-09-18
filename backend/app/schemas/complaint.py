"""群众反映与热线转办相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ComplaintCategory, ComplaintSource, ComplaintStatus, ComplaintVisitResult
from app.schemas.restroom import RestroomBrief


class ComplaintRecordOut(BaseModel):
    """办理流水节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    from_status: str
    to_status: str
    operator: str
    remark: str | None = None
    created_at: datetime


class ComplaintVisitOut(BaseModel):
    """回访记录节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    visitor: str
    visit_time: datetime
    result: str
    note: str | None = None
    next_visit_at: datetime | None = None
    created_at: datetime


class ComplaintBase(BaseModel):
    source: ComplaintSource = Field(default=ComplaintSource.HOTLINE, description="反映来源")
    content: str = Field(min_length=1, max_length=1000, description="反映内容")
    category: ComplaintCategory | None = Field(
        default=None, description="诉求分类，留空按内容自动判定"
    )
    contact_name: str = Field(default="", max_length=60, description="反映人")
    contact_phone: str = Field(default="", max_length=30, description="联系方式")
    assignee: str = Field(default="", max_length=60, description="处理人")


class ComplaintCreate(ComplaintBase):
    restroom_id: int = Field(description="涉及公厕")
    received_at: datetime | None = Field(default=None, description="登记时间，留空取当前时间")
    initial_remark: str | None = Field(default=None, max_length=500, description="受理备注")


class ComplaintUpdate(BaseModel):
    source: ComplaintSource | None = None
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    category: ComplaintCategory | None = None
    contact_name: str | None = Field(default=None, max_length=60)
    contact_phone: str | None = Field(default=None, max_length=30)
    assignee: str | None = Field(default=None, max_length=60)


class ComplaintStatusUpdate(BaseModel):
    """一次办理流转操作；办结待回访时必须填写处理结果。"""

    to_status: ComplaintStatus = Field(description="目标状态")
    operator: str = Field(min_length=1, max_length=60, description="操作人")
    remark: str | None = Field(default=None, max_length=500, description="办理说明")
    result: str | None = Field(default=None, max_length=500, description="处理结果（办结时必填）")


class ComplaintVisitCreate(BaseModel):
    """登记一次回访；未联系上时必须约定再次回访时间。"""

    visitor: str = Field(min_length=1, max_length=60, description="回访人")
    result: ComplaintVisitResult = Field(description="回访结果")
    note: str | None = Field(default=None, max_length=500, description="回访说明")
    visit_time: datetime | None = Field(default=None, description="回访时间，留空取当前时间")
    next_visit_at: datetime | None = Field(default=None, description="再次回访时间（未联系上时必填）")


class ComplaintClassify(BaseModel):
    content: str = Field(min_length=1, max_length=1000, description="反映内容")


class ComplaintClassifyOut(BaseModel):
    category: str
    matched: list[str] = Field(default_factory=list, description="命中的关键词")


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    restroom_id: int
    restroom: RestroomBrief | None = None
    source: str
    content: str
    category: str
    contact_name: str
    contact_phone: str
    assignee: str
    status: str
    received_at: datetime
    result: str | None = None
    handled_at: datetime | None = None
    next_visit_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    records: list[ComplaintRecordOut] = Field(default_factory=list)
    visits: list[ComplaintVisitOut] = Field(default_factory=list)
