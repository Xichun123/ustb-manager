import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Query, Request

from app.dependencies import get_authenticated_session, require_trusted_write_origin
from app.models.courses import (
    CourseAnnouncement,
    CoursePreflightRequest,
    CoursePreflightResponse,
    CourseSelectionContext,
    CourseSelectionLog,
    CourseSelectionPage,
    CourseWriteRequest,
    CourseWriteResponse,
    SelectedCoursePage,
)
from app.services import course_selection_service
from app.services.session_store import Session

router = APIRouter(prefix="/course-selection", tags=["course-selection"])
logger = logging.getLogger(__name__)

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=8, max_length=128),
]


def _audit(request: Request, operation: str, result: dict) -> None:
    logger.info(
        "course_operation operation=%s result=%s request_id=%s",
        operation,
        result["status"],
        getattr(request.state, "request_id", ""),
    )


@router.get("/context", response_model=CourseSelectionContext, summary="获取选课上下文")
async def context(session: Session = Depends(get_authenticated_session)):
    return await course_selection_service.get_context(session)


@router.get("/courses", response_model=CourseSelectionPage, summary="查询可选课程")
async def courses(
    session: Session = Depends(get_authenticated_session),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None, pattern=r"^[123]$"),
    method: str = Query("bx-b-b"),
    college: str = Query(""),
    category: str = Query(""),
    campus: str = Query(""),
    keyword: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await course_selection_service.query_courses(
        session,
        year=year,
        semester=semester,
        method=method,
        college=college,
        category=category,
        campus=campus,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/selected", response_model=SelectedCoursePage, summary="查询已选课程")
async def selected(
    session: Session = Depends(get_authenticated_session),
    year: Optional[str] = Query(None),
    semester: Optional[str] = Query(None, pattern=r"^[123]$"),
):
    return await course_selection_service.query_selected(
        session,
        year=year,
        semester=semester,
    )


@router.get("/cart", response_model=SelectedCoursePage, summary="查询选课购物车")
async def cart(
    session: Session = Depends(get_authenticated_session),
    method: str = Query("bx-b-b"),
):
    return await course_selection_service.query_cart(session, method=method)


@router.get("/logs", response_model=list[CourseSelectionLog], summary="查询选课日志")
async def logs(session: Session = Depends(get_authenticated_session)):
    return await course_selection_service.query_logs(session)


@router.get("/announcements", response_model=list[CourseAnnouncement], summary="查询选课公告")
async def announcements(session: Session = Depends(get_authenticated_session)):
    return await course_selection_service.query_announcements(session)


@router.post(
    "/preflight",
    response_model=CoursePreflightResponse,
    summary="检查选课冲突与业务规则",
)
async def preflight(
    payload: CoursePreflightRequest,
    session: Session = Depends(get_authenticated_session),
):
    return await course_selection_service.preflight(
        session,
        course_id=payload.course_id,
        method=payload.method,
    )


@router.post("/selections", response_model=CourseWriteResponse, summary="选课")
async def create_selection(
    request: Request,
    payload: CourseWriteRequest,
    idempotency_key: IdempotencyKey,
    session: Session = Depends(get_authenticated_session),
    _: None = Depends(require_trusted_write_origin),
):
    result = await course_selection_service.create_selection(
        session,
        course_id=payload.course_id,
        method=payload.method,
        idempotency_key=idempotency_key,
    )
    _audit(request, "select", result)
    return result


@router.delete(
    "/selections/{selection_id}",
    response_model=CourseWriteResponse,
    summary="退课",
)
async def delete_selection(
    request: Request,
    selection_id: str,
    idempotency_key: IdempotencyKey,
    session: Session = Depends(get_authenticated_session),
    _: None = Depends(require_trusted_write_origin),
):
    result = await course_selection_service.delete_selection(
        session,
        selection_id=selection_id,
        idempotency_key=idempotency_key,
    )
    _audit(request, "drop", result)
    return result


@router.post("/cart/items", response_model=CourseWriteResponse, summary="加入选课购物车")
async def add_cart_item(
    request: Request,
    payload: CourseWriteRequest,
    idempotency_key: IdempotencyKey,
    session: Session = Depends(get_authenticated_session),
    _: None = Depends(require_trusted_write_origin),
):
    result = await course_selection_service.add_cart_item(
        session,
        course_id=payload.course_id,
        method=payload.method,
        idempotency_key=idempotency_key,
    )
    _audit(request, "cart-add", result)
    return result


@router.delete(
    "/cart/items/{item_id}",
    response_model=CourseWriteResponse,
    summary="移出选课购物车",
)
async def delete_cart_item(
    request: Request,
    item_id: str,
    idempotency_key: IdempotencyKey,
    session: Session = Depends(get_authenticated_session),
    _: None = Depends(require_trusted_write_origin),
):
    result = await course_selection_service.delete_cart_item(
        session,
        item_id=item_id,
        idempotency_key=idempotency_key,
    )
    _audit(request, "cart-remove", result)
    return result


@router.post("/cart/submit", response_model=CourseWriteResponse, summary="提交选课购物车")
async def submit_cart(
    request: Request,
    idempotency_key: IdempotencyKey,
    session: Session = Depends(get_authenticated_session),
    _: None = Depends(require_trusted_write_origin),
):
    result = await course_selection_service.submit_cart(
        session,
        idempotency_key=idempotency_key,
    )
    _audit(request, "cart-submit", result)
    return result
