from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_authenticated_session
from app.models.courses import (
    CourseSelectionContext,
    CourseSelectionLog,
    CourseSelectionPage,
    SelectedCoursePage,
)
from app.services import course_selection_service
from app.services.session_store import Session

router = APIRouter(prefix="/course-selection", tags=["course-selection"])


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
