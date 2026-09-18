"""群众诉求受理（群众反映与热线转办）接口。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.database import get_db
from app.schemas.common import MessageOut, Page
from app.schemas.complaint import (
    ClassifyPreview,
    ClassifyResult,
    ComplaintAssign,
    ComplaintClose,
    ComplaintCreate,
    ComplaintFinish,
    ComplaintOut,
    ComplaintUpdate,
    FollowUpCreate,
)
from app.services import complaint_service

router = APIRouter(prefix="/complaints", tags=["诉求受理"])


@router.get("", response_model=Page[ComplaintOut], summary="诉求列表")
def list_complaints(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    source: Annotated[str | None, Query(description="诉求来源")] = None,
    category: Annotated[str | None, Query(description="诉求分类")] = None,
    status: Annotated[str | None, Query(description="办理状态")] = None,
    keyword: Annotated[str | None, Query(description="编号/内容/反映人/电话/处理人模糊搜索")] = None,
    follow_due: Annotated[bool, Query(description="仅看已到时待再次回访")] = False,
    date_from: Annotated[date | None, Query(description="受理开始日期")] = None,
    date_to: Annotated[date | None, Query(description="受理结束日期")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "received_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[ComplaintOut]:
    rows, total = complaint_service.list_complaints(
        db,
        restroom_id=restroom_id,
        district=district,
        source=source,
        category=category,
        status=status,
        keyword=keyword,
        follow_due=follow_due or None,
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


@router.post("", response_model=ComplaintOut, status_code=201, summary="受理登记")
def create_complaint(
    payload: ComplaintCreate, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.create_complaint(db, payload))


@router.post("/classify", response_model=ClassifyResult, summary="按内容预判分类")
def classify_complaint(payload: ClassifyPreview) -> ClassifyResult:
    category = complaint_service.classify_complaint(payload.content)
    return ClassifyResult(category=category.value)


@router.get("/{complaint_id}", response_model=ComplaintOut, summary="诉求详情")
def get_complaint(complaint_id: int, db: Annotated[Session, Depends(get_db)]) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.get_complaint(db, complaint_id))


@router.patch("/{complaint_id}", response_model=ComplaintOut, summary="补正登记信息")
def update_complaint(
    complaint_id: int, payload: ComplaintUpdate, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.update_complaint(db, complaint_id, payload))


@router.post("/{complaint_id}/assign", response_model=ComplaintOut, summary="分派/改派处理人")
def assign_handler(
    complaint_id: int, payload: ComplaintAssign, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.assign_handler(db, complaint_id, payload))


@router.post("/{complaint_id}/finish", response_model=ComplaintOut, summary="登记处理结果")
def finish_complaint(
    complaint_id: int, payload: ComplaintFinish, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.finish_complaint(db, complaint_id, payload))


@router.post("/{complaint_id}/follow-ups", response_model=ComplaintOut, summary="登记回访")
def add_follow_up(
    complaint_id: int, payload: FollowUpCreate, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.add_follow_up(db, complaint_id, payload))


@router.post("/{complaint_id}/close", response_model=ComplaintOut, summary="作废关闭")
def close_complaint(
    complaint_id: int, payload: ComplaintClose, db: Annotated[Session, Depends(get_db)]
) -> ComplaintOut:
    return complaint_service.to_out(complaint_service.close_complaint(db, complaint_id, payload))


@router.delete("/{complaint_id}", response_model=MessageOut, summary="删除诉求")
def delete_complaint(complaint_id: int, db: Annotated[Session, Depends(get_db)]) -> MessageOut:
    complaint_service.delete_complaint(db, complaint_id)
    return MessageOut(message="删除成功")
