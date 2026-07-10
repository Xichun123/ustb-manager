from datetime import date as Date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.byyt.academic import get_academic_context
from app.byyt.exams import query_exams
from app.dependencies import get_authenticated_session
from app.models.exams import ExamPage
from app.services.session_store import Session

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("", response_model=ExamPage, summary="查询考试安排")
async def exams(
    session: Session = Depends(get_authenticated_session),
    term: Optional[str] = Query(
        None,
        pattern=r"^\d{4}-\d{4}-[123]$",
        description="学年学期，如 2025-2026-2；默认按今天识别",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if term:
        year, semester = term.rsplit("-", 1)
    else:
        context = await get_academic_context(session, Date.today())
        teaching_term = context["teaching_term"]
        year = teaching_term["year"]
        semester = teaching_term["semester"]
    return await query_exams(
        session,
        year=year,
        semester=semester,
        page=page,
        page_size=page_size,
    )
