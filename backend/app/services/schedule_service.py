from datetime import date
from typing import Dict, List, Optional

from app.byyt.academic import get_academic_context, get_academic_terms
from app.byyt.exams import query_exam_summaries
from app.byyt.schedule import query_schedule as query_current_schedule
from app.byyt.schedule import query_week_options
from app.cache import reference_data_cache
from app.services.session_store import Session


async def get_current_term(session: Session, on_date: Optional[date] = None) -> Dict:
    """获取按日期识别的教学学期，同时避免暑期回落到行政学期。"""
    context = await get_academic_context(session, on_date or date.today())
    teaching_term = context["teaching_term"]
    return {
        "XN": teaching_term["year"],
        "XQ": teaching_term["semester"],
        "XNXQ": teaching_term["code"],
        "ZC": context["week"],
    }


async def get_term_list(session: Session) -> List[Dict]:
    """获取学期列表（带缓存）。"""
    cached = reference_data_cache.get("schedule_term_list")
    if cached is not None:
        return cached

    terms = await get_academic_terms(session)
    formatted = [
        {
            "xn": term["year"],
            "xq": term["semester"],
            "xnxq": term["code"],
            "xqmc": term["name"],
            "xqmc_en": term["name_en"],
            "sfdqxq": "1" if term["is_current"] else "0",
            "dm": f"{term['year']}{term['semester']}",
            "mc": f"{term['year']}学年第{term['semester']}学期",
        }
        for term in terms
    ]
    reference_data_cache.set("schedule_term_list", formatted)
    return formatted


async def get_week_list(
    session: Session,
    xn: Optional[str] = None,
    xq: Optional[str] = None,
) -> List[Dict]:
    """获取周次列表。"""
    return await query_week_options(session, year=xn, semester=xq)


async def get_schedule_with_dates(
    session: Session,
    xn: str,
    xq: str,
    week: Optional[int] = None,
) -> Dict:
    """兼容旧客户端的课表响应，数据源使用当前详细课表接口。"""
    view = await query_current_schedule(
        session,
        year=xn,
        semester=xq,
        week=week,
    )
    schedule = []
    for course in view["items"]:
        period = (course["start_period"] - 1) // 2 + 1
        schedule.append(
            {
                "key": f"xq{course['weekday']}_jc{period}",
                "weekday": course["weekday"],
                "period": period,
                "start_period": course["start_period"],
                "end_period": course["end_period"],
                "course_name": course["course_name"],
                "course_name_en": course["course_name_en"],
                "teacher": course["teacher"],
                "weeks": course["week_text"],
                "location": course["location"],
                "period_text": course["period_text"],
                "task_code": course["task_code"],
                "week_bitmap": ",".join(str(value) for value in course["weeks"]),
            }
        )

    return {
        "schedule": schedule,
        "dates": view["dates"],
        "week": week,
        "term": view["term"],
    }


async def get_exam_schedule(session: Session) -> List[Dict]:
    """获取考试安排。"""
    return await query_exam_summaries(session)
