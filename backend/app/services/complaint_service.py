"""群众诉求受理业务逻辑：登记、分类、分派、办结、回访。"""

from datetime import date, datetime, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    COMPLAINT_CATEGORY_KEYWORDS,
    COMPLAINT_TRANSITIONS,
    ComplaintCategory,
    ComplaintStatus,
    FollowUpResult,
)
from app.core.exceptions import DomainError, NotFoundError
from app.models import Complaint, ComplaintFlowRecord, FollowUpRecord, Restroom
from app.schemas.complaint import (
    ComplaintAssign,
    ComplaintClose,
    ComplaintCreate,
    ComplaintFinish,
    ComplaintOut,
    ComplaintUpdate,
    FollowUpCreate,
)
from app.services import restroom_service

SORTABLE_FIELDS = {
    "received_at": Complaint.received_at,
    "status": Complaint.status,
    "category": Complaint.category,
    "code": Complaint.code,
    "next_follow_time": Complaint.next_follow_time,
    "updated_at": Complaint.updated_at,
}


def _next_code(db: Session) -> str:
    """生成形如 SQ-20240913-001 的诉求编号。"""
    prefix = datetime.now().strftime("SQ-%Y%m%d")
    seq = (
        db.scalar(
            select(func.count()).select_from(Complaint).where(Complaint.code.like(f"{prefix}-%"))
        )
        or 0
    ) + 1
    while True:
        code = f"{prefix}-{seq:03d}"
        if not db.scalar(select(Complaint.id).where(Complaint.code == code)):
            return code
        seq += 1


def classify_complaint(content: str) -> ComplaintCategory:
    """按反映内容命中关键词判定分类，均未命中时归为「其他」。"""
    text = content or ""
    for category, keywords in COMPLAINT_CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return ComplaintCategory(category)
    return ComplaintCategory.OTHER


def get_complaint(db: Session, complaint_id: int) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise NotFoundError(f"诉求 {complaint_id} 不存在")
    return complaint


def to_out(complaint: Complaint) -> ComplaintOut:
    return ComplaintOut.model_validate(complaint)


def _values(data: dict) -> dict:
    return {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}


def _append_record(
    complaint: Complaint,
    *,
    action: str,
    from_status: str,
    to_status: str,
    operator: str,
    remark: str | None,
) -> None:
    complaint.records.append(
        ComplaintFlowRecord(
            action=action,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
            remark=remark,
        )
    )


def list_complaints(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    source: str | None = None,
    category: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    follow_due: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "received_at",
    order: str = "desc",
) -> tuple[list[Complaint], int]:
    stmt = select(Complaint)
    if district:
        stmt = stmt.join(Restroom, Restroom.id == Complaint.restroom_id).where(
            Restroom.district == district
        )
    if restroom_id:
        stmt = stmt.where(Complaint.restroom_id == restroom_id)
    if source:
        stmt = stmt.where(Complaint.source == source)
    if category:
        stmt = stmt.where(Complaint.category == category)
    if status:
        stmt = stmt.where(Complaint.status == status)
    if date_from:
        stmt = stmt.where(Complaint.received_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Complaint.received_at <= datetime.combine(date_to, time.max))
    if follow_due:
        # 到了约定时间仍未回访的诉求，提醒安排再次回访
        stmt = stmt.where(
            Complaint.status == ComplaintStatus.FOLLOW_UP.value,
            Complaint.next_follow_time.is_not(None),
            Complaint.next_follow_time <= datetime.now(),
        )
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Complaint.code.like(like),
                Complaint.content.like(like),
                Complaint.reporter_name.like(like),
                Complaint.reporter_phone.like(like),
                Complaint.handler.like(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, Complaint.received_at)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Complaint.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def create_complaint(db: Session, payload: ComplaintCreate) -> Complaint:
    restroom_service.get_restroom(db, payload.restroom_id)
    category = payload.category or classify_complaint(payload.content)
    complaint = Complaint(
        code=_next_code(db),
        restroom_id=payload.restroom_id,
        source=payload.source.value,
        content=payload.content,
        category=category.value,
        status=ComplaintStatus.PENDING.value,
        reporter_name=payload.reporter_name,
        reporter_phone=payload.reporter_phone,
        receiver=payload.receiver,
        received_at=payload.received_at or datetime.now(),
    )
    _append_record(
        complaint,
        action="受理登记",
        from_status="",
        to_status=ComplaintStatus.PENDING.value,
        operator=payload.receiver or "值班坐席",
        remark=payload.initial_remark or f"{payload.source.value}受理，分类判定为「{category.value}」",
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def update_complaint(db: Session, complaint_id: int, payload: ComplaintUpdate) -> Complaint:
    complaint = get_complaint(db, complaint_id)
    if complaint.status in (ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value):
        raise DomainError(f"诉求已{complaint.status}，无法再修改登记信息")
    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"] is None:
        # 分类显式置空：按内容自动判定
        data["category"] = classify_complaint(data.get("content") or complaint.content)
    elif "content" in data and "category" not in data:
        # 仅修改内容未指定分类：按新内容重新判定
        data["category"] = classify_complaint(data["content"])
    for key, value in _values(data).items():
        setattr(complaint, key, value)
    db.commit()
    db.refresh(complaint)
    return complaint


def assign_handler(db: Session, complaint_id: int, payload: ComplaintAssign) -> Complaint:
    """分派处理人：待分派 -> 处理中；处理中再次分派视为改派。"""
    complaint = get_complaint(db, complaint_id)
    if complaint.status not in (ComplaintStatus.PENDING.value, ComplaintStatus.PROCESSING.value):
        raise DomainError(f"当前状态「{complaint.status}」不允许分派处理人")
    reassign = complaint.status == ComplaintStatus.PROCESSING.value
    complaint.handler = payload.handler
    complaint.assigned_at = datetime.now()
    complaint.status = ComplaintStatus.PROCESSING.value
    _append_record(
        complaint,
        action="改派处理人" if reassign else "分派处理人",
        from_status=ComplaintStatus.PROCESSING.value if reassign else ComplaintStatus.PENDING.value,
        to_status=ComplaintStatus.PROCESSING.value,
        operator=payload.operator,
        remark=payload.remark or f"分派给「{payload.handler}」办理",
    )
    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def finish_complaint(db: Session, complaint_id: int, payload: ComplaintFinish) -> Complaint:
    """处理完成并登记结果：处理中 -> 待回访。"""
    complaint = get_complaint(db, complaint_id)
    if complaint.status != ComplaintStatus.PROCESSING.value:
        raise DomainError(f"当前状态「{complaint.status}」不允许登记处理结果，请先分派处理人")
    complaint.result = payload.result
    complaint.finished_at = datetime.now()
    complaint.status = ComplaintStatus.FOLLOW_UP.value
    _append_record(
        complaint,
        action="登记处理结果",
        from_status=ComplaintStatus.PROCESSING.value,
        to_status=ComplaintStatus.FOLLOW_UP.value,
        operator=payload.operator,
        remark=payload.remark or payload.result,
    )
    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def add_follow_up(db: Session, complaint_id: int, payload: FollowUpCreate) -> Complaint:
    """登记回访：联系上则办结；未联系上则约定下次回访时间，保持待回访。"""
    complaint = get_complaint(db, complaint_id)
    if complaint.status != ComplaintStatus.FOLLOW_UP.value:
        raise DomainError(f"当前状态「{complaint.status}」不在回访环节")

    reached = payload.result == FollowUpResult.REACHED
    if reached and payload.next_follow_time is not None:
        raise DomainError("已联系上的回访无需再约定下次回访时间")
    if not reached and payload.next_follow_time is None:
        raise DomainError("未联系上反映人，请填写下次回访时间以安排再次回访")
    if not reached and payload.satisfaction is not None:
        raise DomainError("未联系上反映人时无需填写满意度")

    complaint.follow_ups.append(
        FollowUpRecord(
            result=payload.result.value,
            satisfaction=payload.satisfaction.value if payload.satisfaction else None,
            operator=payload.operator,
            remark=payload.remark,
        )
    )
    if reached:
        complaint.status = ComplaintStatus.RESOLVED.value
        complaint.next_follow_time = None
        action = "回访办结"
        remark = payload.remark or (
            f"已联系上反映人，满意度：{payload.satisfaction.value}"
            if payload.satisfaction
            else "已联系上反映人，诉求办结"
        )
    else:
        complaint.next_follow_time = payload.next_follow_time
        action = "回访未联系上"
        remark = payload.remark or "未联系上反映人，已安排再次回访"
    _append_record(
        complaint,
        action=action,
        from_status=ComplaintStatus.FOLLOW_UP.value,
        to_status=complaint.status,
        operator=payload.operator,
        remark=remark,
    )
    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def close_complaint(db: Session, complaint_id: int, payload: ComplaintClose) -> Complaint:
    """作废关闭：仅待分派、处理中的诉求可关闭。"""
    complaint = get_complaint(db, complaint_id)
    allowed = COMPLAINT_TRANSITIONS.get(complaint.status, [])
    if ComplaintStatus.CLOSED.value not in allowed:
        raise DomainError(f"当前状态「{complaint.status}」不允许关闭")
    from_status = complaint.status
    complaint.status = ComplaintStatus.CLOSED.value
    complaint.closed_at = datetime.now()
    complaint.next_follow_time = None
    _append_record(
        complaint,
        action="作废关闭",
        from_status=from_status,
        to_status=ComplaintStatus.CLOSED.value,
        operator=payload.operator,
        remark=payload.remark or "诉求作废关闭",
    )
    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def delete_complaint(db: Session, complaint_id: int) -> None:
    complaint = get_complaint(db, complaint_id)
    db.delete(complaint)
    db.commit()
