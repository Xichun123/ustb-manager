from datetime import date as Date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.byyt.academic import get_academic_calendar, get_academic_context, get_academic_terms
from app.byyt.progress import (
    query_academic_progress,
    query_academic_progress_courses,
    query_academic_progress_modules,
)
from app.byyt.warnings import query_academic_warnings
from app.dependencies import get_authenticated_session
from app.models.academic import (
    AcademicCalendar,
    AcademicProgress,
    AcademicProgressCourses,
    AcademicProgressModules,
    AcademicWarning,
)
from app.services.session_store import Session

router = APIRouter(prefix="/academic", tags=["academic"])


class AcademicTerm(BaseModel):
    year: str = Field(..., description="学年，如 2025-2026")
    semester: str = Field(..., description="学期代码，1/2/3")
    code: str = Field(..., description="规范化学年学期代码")


class AcademicTermOption(AcademicTerm):
    name: str = ""
    name_en: str = ""
    is_current: bool = False


class AcademicContextResponse(BaseModel):
    date: str
    administrative_term: AcademicTerm
    teaching_term: AcademicTerm
    week: Optional[int] = None
    is_in_teaching_week: bool


@router.get("/terms", response_model=list[AcademicTermOption], summary="获取学年学期列表")
async def academic_terms(session: Session = Depends(get_authenticated_session)):
    return await get_academic_terms(session)


@router.get("/progress", response_model=AcademicProgress, summary="查询学业进度汇总")
async def academic_progress(
    term: Optional[str] = Query(
        None,
        pattern=r"^\d{4}-\d{4}-[123]$",
        description="截止学年学期；不传则查询全部学期",
    ),
    session: Session = Depends(get_authenticated_session),
):
    return await query_academic_progress(session, cutoff_term=term)


@router.get(
    "/progress/modules",
    response_model=AcademicProgressModules,
    summary="查询学业进度模块要求",
)
async def academic_progress_modules(
    session: Session = Depends(get_authenticated_session),
):
    return await query_academic_progress_modules(session)


@router.get(
    "/progress/courses",
    response_model=AcademicProgressCourses,
    summary="查询学业进度课程要求",
)
async def academic_progress_courses(
    session: Session = Depends(get_authenticated_session),
):
    return await query_academic_progress_courses(session)


@router.get("/warnings", response_model=AcademicWarning, summary="查询学业警示")
async def academic_warnings(
    term: Optional[str] = Query(
        None,
        pattern=r"^\d{4}-\d{4}-[123]$",
        description="学年学期；默认使用学业警示模块当前学期",
    ),
    session: Session = Depends(get_authenticated_session),
):
    return await query_academic_warnings(session, term=term)


@router.get("/calendar", response_model=AcademicCalendar, summary="获取学期校历")
async def academic_calendar(
    term: str = Query(..., pattern=r"^\d{4}-\d{4}-[123]$", description="学年学期代码"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    session: Session = Depends(get_authenticated_session),
):
    return await get_academic_calendar(session, term=term, month=month)


@router.get("/context", response_model=AcademicContextResponse, summary="获取日期感知教学上下文")
async def academic_context(
    on_date: Optional[Date] = Query(None, alias="date", description="查询日期，默认今天"),
    session: Session = Depends(get_authenticated_session),
):
    return await get_academic_context(session, on_date or Date.today())
