"""群众反映与热线转办接口。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.constants import OPEN_COMPLAINT_STATUSES
from app.core.database import get_db
from app.schemas.common import MessageOut, Page
from app.schemas.complaint import (
    ComplaintClassify,
    ComplaintClassifyOut,
    ComplaintCreate,
    ComplaintOut,
    ComplaintStatusUpdate,
    ComplaintUpdate,
    ComplaintVisitCreate,
)
from app.services import complaint_service

router = APIRouter(prefix="/complaints", tags=["群众反映"])


class TransitionOption(BaseModel):
    status: str
    action: str


@router.get("", response_model=Page[ComplaintOut], summary="诉求列表")
def list_complaints(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    status: Annotated[str | None, Query(description="办理状态")] = None,
    open_only: Annotated[bool, Query(description="仅看未闭环诉求")] = False,
    source: Annotated[str | None, Query(description="反映来源")] = None,
    category: Annotated[str | None, Query(description="诉求分类")] = None,
    keyword: Annotated[str | None, Query(description="内容/编号/反映人/联系方式模糊搜索")] = None,
    visit_due: Annotated[bool, Query(description="仅看当前需要回访的诉求")] = False,
    date_from: Annotated[date | None, Query(description="登记开始日期")] = None,
    date_to: Annotated[date | None, Query(description="登记结束日期")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "received_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[ComplaintOut]:
    statuses = list(OPEN_COMPLAINT_STATUSES) if open_only else None
    rows, total = complaint_service.list_complaints(
        db,
        restroom_id=restroom_id,
        district=district,
        status=status,
        statuses=statuses,
        source=source,
        category=category,
        keyword=keyword,
        visit_due=visit_due or None,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[ComplaintOut](
        items=[complaint_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=ComplaintOut, status_code=201, summary="登记受理")
def create_complaint(
    payload: ComplaintCreate, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.create_complaint(db, payload))


@router.post("/classify", response_model=ComplaintClassifyOut, summary="按内容智能判定分类")
def classify(payload: ComplaintClassify) -> ComplaintClassifyOut:
    category, matched = complaint_service.classify_content(payload.content)
    return ComplaintClassifyOut(category=category, matched=matched)


@router.get("/{complaint_id}", response_model=ComplaintOut, summary="诉求详情与办理轨迹")
def get_complaint(complaint_id: int, db: Annotated[Session, Depends(get_db)]) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.get_complaint(db, complaint_id))


@router.patch("/{complaint_id}", response_model=ComplaintOut, summary="更新诉求信息")
def update_complaint(
    complaint_id: int, payload: ComplaintUpdate, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.update_complaint(db, complaint_id, payload))


@router.post("/{complaint_id}/transitions", response_model=ComplaintOut, summary="推进办理状态")
def change_status(
    complaint_id: int,
    payload: ComplaintStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.change_status(db, complaint_id, payload))


@router.get(
    "/{complaint_id}/transitions",
    response_model=list[TransitionOption],
    summary="可执行的办理动作",
)
def list_transitions(
    complaint_id: int, db: Annotated[Session, Depends(get_db)]
) -> list[TransitionOption]:
    complaint = complaint_service.get_complaint(db, complaint_id)
    return [
        TransitionOption(**option) for option in complaint_service.allowed_transitions(complaint)
    ]


@router.post("/{complaint_id}/visits", response_model=ComplaintOut, summary="登记回访")
def add_visit(
    complaint_id: int,
    payload: ComplaintVisitCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.add_visit(db, complaint_id, payload))


@router.delete("/{complaint_id}", response_model=MessageOut, summary="删除诉求")
def delete_complaint(complaint_id: int, db: Annotated[Session, Depends(get_db)]) -> MessageOut:
    complaint_service.delete_complaint(db, complaint_id)
    return MessageOut(message="删除成功")
