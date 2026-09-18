"""群众反映与热线转办业务逻辑。"""

from datetime import date, datetime, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    COMPLAINT_CATEGORY_KEYWORDS,
    COMPLAINT_TRANSITION_ACTIONS,
    COMPLAINT_TRANSITIONS,
    OPEN_COMPLAINT_STATUSES,
    ComplaintCategory,
    ComplaintStatus,
    ComplaintVisitResult,
)
from app.core.exceptions import DomainError, NotFoundError
from app.models import Complaint, ComplaintRecord, ComplaintVisit, Restroom
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintOut,
    ComplaintStatusUpdate,
    ComplaintUpdate,
    ComplaintVisitCreate,
)
from app.services import restroom_service

SORTABLE_FIELDS = {
    "received_at": Complaint.received_at,
    "status": Complaint.status,
    "category": Complaint.category,
    "code": Complaint.code,
    "next_visit_at": Complaint.next_visit_at,
    "updated_at": Complaint.updated_at,
}


def _next_code(db: Session) -> str:
    prefix = datetime.now().strftime("FS-%Y%m%d")
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


def _values(data: dict) -> dict:
    return {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}


def classify_content(content: str) -> tuple[str, list[str]]:
    """按反映内容判定分类：统计各分类关键词命中数，返回得分最高的分类。"""
    text = (content or "").strip()
    best_category = ComplaintCategory.OTHER.value
    best_hits: list[str] = []
    for category, keywords in COMPLAINT_CATEGORY_KEYWORDS.items():
        hits = [word for word in keywords if word in text]
        if len(hits) > len(best_hits):
            best_category = category
            best_hits = hits
    return best_category, best_hits


def get_complaint(db: Session, complaint_id: int) -> Complaint:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise NotFoundError(f"诉求 {complaint_id} 不存在")
    return complaint


def to_out(complaint: Complaint) -> ComplaintOut:
    return ComplaintOut.model_validate(complaint)


def list_complaints(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    status: str | None = None,
    statuses: list[str] | None = None,
    source: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    visit_due: bool | None = None,
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
    if status:
        stmt = stmt.where(Complaint.status == status)
    if statuses:
        stmt = stmt.where(Complaint.status.in_(statuses))
    if source:
        stmt = stmt.where(Complaint.source == source)
    if category:
        stmt = stmt.where(Complaint.category == category)
    if date_from:
        stmt = stmt.where(Complaint.received_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Complaint.received_at <= datetime.combine(date_to, time.max))
    if visit_due:
        # 待回访且未约下次回访，或约定的再次回访时间已到
        stmt = stmt.where(
            Complaint.status == ComplaintStatus.PENDING_VISIT.value,
            or_(
                Complaint.next_visit_at.is_(None),
                Complaint.next_visit_at <= datetime.now(),
            ),
        )
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Complaint.content.like(like),
                Complaint.code.like(like),
                Complaint.contact_name.like(like),
                Complaint.contact_phone.like(like),
                Complaint.assignee.like(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, Complaint.received_at)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Complaint.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def create_complaint(db: Session, payload: ComplaintCreate) -> Complaint:
    restroom_service.get_restroom(db, payload.restroom_id)

    data = _values(payload.model_dump(exclude={"received_at", "initial_remark"}))
    if not data.get("category"):
        data["category"], _ = classify_content(payload.content)
    complaint = Complaint(
        code=_next_code(db),
        received_at=payload.received_at or datetime.now(),
        status=ComplaintStatus.PENDING.value,
        **data,
    )
    complaint.records.append(
        ComplaintRecord(
            action="登记受理",
            from_status="",
            to_status=ComplaintStatus.PENDING.value,
            operator=payload.contact_name or "值班员",
            remark=payload.initial_remark or f"{complaint.source}登记，等待受理分派",
        )
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def update_complaint(db: Session, complaint_id: int, payload: ComplaintUpdate) -> Complaint:
    complaint = get_complaint(db, complaint_id)
    for key, value in _values(payload.model_dump(exclude_unset=True)).items():
        setattr(complaint, key, value)
    db.commit()
    db.refresh(complaint)
    return complaint


def allowed_transitions(complaint: Complaint) -> list[dict[str, str]]:
    return [
        {
            "status": target,
            "action": COMPLAINT_TRANSITION_ACTIONS.get((complaint.status, target), "状态变更"),
        }
        for target in COMPLAINT_TRANSITIONS.get(complaint.status, [])
    ]


def _append_record(
    complaint: Complaint, action: str, from_status: str, operator: str, remark: str | None
) -> None:
    complaint.records.append(
        ComplaintRecord(
            action=action,
            from_status=from_status,
            to_status=complaint.status,
            operator=operator,
            remark=remark,
        )
    )


def change_status(db: Session, complaint_id: int, payload: ComplaintStatusUpdate) -> Complaint:
    complaint = get_complaint(db, complaint_id)
    target = payload.to_status.value
    if target == complaint.status:
        raise DomainError(f"诉求已处于「{target}」状态")
    allowed = COMPLAINT_TRANSITIONS.get(complaint.status, [])
    if target not in allowed:
        hint = "、".join(allowed) if allowed else "无（请通过登记回访推进）"
        raise DomainError(f"当前状态「{complaint.status}」不允许流转到「{target}」，可选：{hint}")
    if target == ComplaintStatus.PENDING_VISIT.value and not (payload.result or "").strip():
        raise DomainError("办结前请填写处理结果，便于回访时向反映人反馈")

    from_status = complaint.status
    complaint.status = target
    if target == ComplaintStatus.PROCESSING.value and payload.operator and not complaint.assignee:
        complaint.assignee = payload.operator
    if target == ComplaintStatus.PENDING_VISIT.value:
        complaint.result = payload.result.strip()
        complaint.handled_at = datetime.now()
        complaint.next_visit_at = None
    complaint.closed_at = datetime.now() if target == ComplaintStatus.CLOSED.value else None
    _append_record(
        complaint,
        COMPLAINT_TRANSITION_ACTIONS.get((from_status, target), "状态变更"),
        from_status,
        payload.operator,
        payload.remark,
    )
    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def add_visit(db: Session, complaint_id: int, payload: ComplaintVisitCreate) -> Complaint:
    """登记回访：满意办结、不满意退回重新处理、未联系上则安排再次回访。"""
    complaint = get_complaint(db, complaint_id)
    if complaint.status != ComplaintStatus.PENDING_VISIT.value:
        raise DomainError(f"当前状态「{complaint.status}」无需回访，仅「待回访」状态可登记回访")
    if payload.result == ComplaintVisitResult.UNREACHABLE and payload.next_visit_at is None:
        raise DomainError("未联系上反映人，请约定再次回访时间")

    visit = ComplaintVisit(
        visitor=payload.visitor,
        visit_time=payload.visit_time or datetime.now(),
        result=payload.result.value,
        note=payload.note,
        next_visit_at=payload.next_visit_at if payload.result == ComplaintVisitResult.UNREACHABLE else None,
    )
    complaint.visits.append(visit)

    from_status = complaint.status
    if payload.result == ComplaintVisitResult.SATISFIED:
        complaint.status = ComplaintStatus.DONE.value
        complaint.next_visit_at = None
        action = COMPLAINT_TRANSITION_ACTIONS[(from_status, ComplaintStatus.DONE.value)]
    elif payload.result == ComplaintVisitResult.UNSATISFIED:
        complaint.status = ComplaintStatus.PROCESSING.value
        complaint.next_visit_at = None
        action = COMPLAINT_TRANSITION_ACTIONS[(from_status, ComplaintStatus.PROCESSING.value)]
    else:
        complaint.next_visit_at = payload.next_visit_at
        action = "回访未联系上"
    _append_record(complaint, action, from_status, payload.visitor, payload.note)

    db.commit()
    db.refresh(complaint)
    restroom_service.touch(db, complaint.restroom_id)
    return complaint


def delete_complaint(db: Session, complaint_id: int) -> None:
    complaint = get_complaint(db, complaint_id)
    db.delete(complaint)
    db.commit()


def is_open(complaint: Complaint) -> bool:
    return complaint.status in OPEN_COMPLAINT_STATUSES
