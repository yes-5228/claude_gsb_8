"""群众反映与热线转办模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ComplaintCategory, ComplaintSource, ComplaintStatus
from app.core.database import Base


class Complaint(Base):
    """群众通过热线、现场、网络等渠道反映的公厕诉求，需要办理与回访闭环。"""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="受理编号")
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="涉及公厕"
    )
    source: Mapped[str] = mapped_column(
        String(20), default=ComplaintSource.HOTLINE.value, index=True, comment="反映来源"
    )
    content: Mapped[str] = mapped_column(Text, default="", comment="反映内容")
    category: Mapped[str] = mapped_column(
        String(30), default=ComplaintCategory.OTHER.value, index=True, comment="诉求分类"
    )
    contact_name: Mapped[str] = mapped_column(String(60), default="", comment="反映人")
    contact_phone: Mapped[str] = mapped_column(String(30), default="", comment="联系方式")
    assignee: Mapped[str] = mapped_column(String(60), default="", comment="处理人")
    status: Mapped[str] = mapped_column(
        String(20), default=ComplaintStatus.PENDING.value, index=True, comment="办理状态"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="登记时间"
    )
    result: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理结果")
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="办结时间")
    next_visit_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="下次回访时间"
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="关闭时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    restroom: Mapped["Restroom"] = relationship(back_populates="complaints")  # noqa: F821
    records: Mapped[list["ComplaintRecord"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintRecord.created_at",
    )
    visits: Mapped[list["ComplaintVisit"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintVisit.visit_time",
    )


class ComplaintRecord(Base):
    """投诉办理流水，还原受理、分派、办结、回访、关闭的完整轨迹。"""

    __tablename__ = "complaint_records"

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


class ComplaintVisit(Base):
    """回访记录：办结后联系反映人，未联系上的安排再次回访。"""

    __tablename__ = "complaint_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True, comment="所属诉求"
    )
    visitor: Mapped[str] = mapped_column(String(60), default="", comment="回访人")
    visit_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="回访时间"
    )
    result: Mapped[str] = mapped_column(String(20), comment="回访结果")
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="回访说明")
    next_visit_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="再次回访时间"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    complaint: Mapped["Complaint"] = relationship(back_populates="visits")
