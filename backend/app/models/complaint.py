"""群众诉求受理（群众反映与热线转办）模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ComplaintSource, ComplaintStatus
from app.core.database import Base


class Complaint(Base):
    """一条群众诉求：登记来源与反映内容，分派处理并回访办结。"""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="诉求编号")
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="涉及公厕"
    )
    source: Mapped[str] = mapped_column(
        String(20), default=ComplaintSource.PUBLIC.value, index=True, comment="诉求来源"
    )
    content: Mapped[str] = mapped_column(Text, comment="反映内容")
    category: Mapped[str] = mapped_column(String(20), index=True, comment="诉求分类")
    status: Mapped[str] = mapped_column(
        String(20), default=ComplaintStatus.PENDING.value, index=True, comment="办理状态"
    )
    reporter_name: Mapped[str] = mapped_column(String(60), default="", comment="反映人姓名")
    reporter_phone: Mapped[str] = mapped_column(String(30), comment="联系电话")
    receiver: Mapped[str] = mapped_column(String(60), default="", comment="受理人")
    handler: Mapped[str] = mapped_column(String(60), default="", comment="处理人")
    result: Mapped[str] = mapped_column(Text, default="", comment="处理结果")
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="受理时间"
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="分派时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="办结时间")
    next_follow_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="下次回访时间"
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="关闭时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    restroom: Mapped["Restroom"] = relationship(back_populates="complaints")  # noqa: F821
    records: Mapped[list["ComplaintFlowRecord"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintFlowRecord.created_at",
    )
    follow_ups: Mapped[list["FollowUpRecord"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="FollowUpRecord.created_at",
    )


class ComplaintFlowRecord(Base):
    """诉求办理流水，还原受理、分派、办结、回访的完整轨迹。"""

    __tablename__ = "complaint_flow_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True, comment="所属诉求"
    )
    action: Mapped[str] = mapped_column(String(30), comment="办理动作")
    from_status: Mapped[str] = mapped_column(String(20), default="", comment="原状态")
    to_status: Mapped[str] = mapped_column(String(20), comment="新状态")
    operator: Mapped[str] = mapped_column(String(60), default="", comment="操作人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="办理说明")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="操作时间"
    )

    complaint: Mapped["Complaint"] = relationship(back_populates="records")


class FollowUpRecord(Base):
    """一次回访记录；未联系上时会约定下次回访时间。"""

    __tablename__ = "follow_up_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True, comment="所属诉求"
    )
    result: Mapped[str] = mapped_column(String(20), comment="回访结果")
    satisfaction: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="满意度")
    operator: Mapped[str] = mapped_column(String(60), default="", comment="回访人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="回访备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="回访时间"
    )

    complaint: Mapped["Complaint"] = relationship(back_populates="follow_ups")
