import asyncio
import logging
from datetime import date
from typing import Dict, List, Optional
from app.byyt.academic import get_academic_context
from app.byyt.schedule import query_schedule as query_current_schedule
from app.services.session_store import Session
from app.exceptions import BYYTSessionExpired
from app.services.grades_service import _check_byyt_response
from app.services.byyt_crypto import encrypt_empty
from app.cache import reference_data_cache

logger = logging.getLogger(__name__)


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
    """获取学期列表（带缓存）"""
    cached = reference_data_cache.get("schedule_term_list")
    if cached is not None:
        return cached

    def _fetch():
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/queryXnxq",
            data={"data": encrypt_empty()},
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)
    # BYYT返回格式为 {"code": 200, "content": [...]}
    if isinstance(result, dict):
        # 检查是否有错误
        if result.get("code") != 200:
            logger.warning(f"BYYT queryXnxq error: {result.get('msg', result.get('content', 'Unknown error'))}")
            raise BYYTSessionExpired(f"BYYT error: {result.get('msg', 'Unknown error')}")
        terms = result.get("content", [])
    else:
        terms = result if isinstance(result, list) else []

    # 转换为前端期望的格式
    formatted = []
    for t in terms:
        xn = t.get("xn", "")
        xq = t.get("xq", "")
        formatted.append({
            **t,
            "dm": f"{xn}{xq}",  # 代码: 2025-20262 (与BYYT p_xnxq格式一致)
            "mc": f"{xn}学年第{xq}学期",  # 名称: 2025-2026学年第2学期
        })
    reference_data_cache.set("schedule_term_list", formatted)
    return formatted
async def get_week_list(
    session: Session,
    xn: Optional[str] = None,
    xq: Optional[str] = None,
) -> List[Dict]:
    """获取周次列表"""

    def _fetch():
        params = {
            "xn": xn or "",
            "xq": xq or "",
        }
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/queryzclist",
            data=params,
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)
    return result if isinstance(result, list) else []


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
    """获取考试安排"""

    def _fetch():
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/queryKsxxByXs",
            data="",
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)

    # Parse and return the exam list
    if isinstance(result, list):
        return _parse_exam_schedule(result)
    return []


def _parse_exam_schedule(exams: List[Dict]) -> List[Dict]:
    """解析考试安排数据，转换为前端友好的格式"""
    parsed = []
    for exam in exams:
        parsed.append({
            "course_code": exam.get("KCDM", ""),
            "course_name": exam.get("KCMC", ""),
            "course_name_en": exam.get("KCMC_EN", ""),
            "exam_type": exam.get("KSSJDMC", ""),  # 期末/期中
            "exam_date": exam.get("KSRQ", ""),
            "exam_date_display": exam.get("KSRQ2", ""),
            "exam_time": exam.get("KSJTSJ", ""),
            "weekday": exam.get("XQJMC", ""),
            "week_number": exam.get("DJZ", 0),
            "start_period": exam.get("KSJC", 0),
            "end_period": exam.get("JSJC", 0),
            "building": exam.get("JXLMC", ""),
            "room": exam.get("JXCDMC", ""),
            "campus": exam.get("XIAOQUBMC", ""),
            "term": exam.get("XNXQMC", ""),
            "remark": exam.get("JKJSBZ", ""),
            "raw": exam,
        })
    return parsed
