import asyncio
import logging
from typing import Dict, List, Optional
from app.services.session_store import Session
from app.exceptions import BYYTSessionExpired
from app.services.grades_service import _check_byyt_response
from app.services.byyt_crypto import encrypt, encrypt_empty
from app.cache import reference_data_cache

logger = logging.getLogger(__name__)


async def get_current_term(session: Session) -> Dict:
    """获取当前学年学期"""

    def _fetch():
        # This API doesn't require encrypted data
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/querydangqianxnxq",
            data="",
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)
    # This API returns data directly: {"XN": "2025-2026", "XQ": "1", ...}
    # Not wrapped in {"code": 200, "content": {...}}
    if isinstance(result, dict):
        # Check if it's an error response with code field
        if "code" in result and result.get("code") != 200:
            logger.warning(f"BYYT querydangqianxnxq error: {result.get('msg', result.get('content', 'Unknown error'))}")
            raise BYYTSessionExpired(f"BYYT error: {result.get('msg', 'Unknown error')}")
        # If it has XN field, it's a valid direct response
        if "XN" in result:
            return result
        # Fall back to extracting content if wrapped
        return result.get("content", result)
    return result


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


async def get_week_dates(
    session: Session,
    xn: str,
    xq: str,
    week: int,
) -> List[Dict]:
    """获取指定周的日期列表"""

    def _fetch():
        params = {
            "xn": xn,
            "xq": xq,
            "djz": str(week),
        }
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/queryRlZcSj",
            data=params,
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)
    if isinstance(result, dict) and result.get("code") == 200:
        return result.get("content", [])
    return result if isinstance(result, list) else []


async def get_full_schedule(
    session: Session,
    xn: str,
    xq: str,
) -> List[Dict]:
    """获取总课表"""

    def _fetch():
        params = {
            "xn": xn,
            "xq": xq,
        }
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/xszykb/queryxszykbzong",
            data=params,
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)
    return _parse_schedule(result if isinstance(result, list) else [])


async def get_week_schedule(
    session: Session,
    xn: str,
    xq: str,
    week: int,
) -> List[Dict]:
    """获取周课表"""

    def _fetch():
        params = {
            "xn": xn,
            "xq": xq,
            "zc": str(week),
        }
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/xszykb/queryxszykbzhou",
            data=params,
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)
    return _parse_schedule(result if isinstance(result, list) else [])


def _parse_schedule(courses: List[Dict]) -> List[Dict]:
    """解析课表数据，转换为前端友好的格式"""
    parsed = []
    for course in courses:
        # 解析KEY获取星期和节次
        key = course.get("KEY", "")
        weekday = 0
        period = 0
        if key.startswith("xq") and "_jc" in key:
            try:
                parts = key.split("_")
                weekday = int(parts[0].replace("xq", ""))
                period = int(parts[1].replace("jc", ""))
            except (ValueError, IndexError):
                pass

        # 解析SKSJ获取详细信息
        sksj = course.get("SKSJ", "")
        lines = sksj.split("\n") if sksj else []

        course_name = lines[0] if len(lines) > 0 else ""
        teacher = lines[1] if len(lines) > 1 else ""
        weeks = lines[2] if len(lines) > 2 else ""
        location = lines[3] if len(lines) > 3 else ""
        period_text = lines[4] if len(lines) > 4 else ""

        # 解析英文信息
        sksj_en = course.get("SKSJ_EN", "")
        lines_en = sksj_en.split("\n") if sksj_en else []
        course_name_en = lines_en[0] if len(lines_en) > 0 else ""

        parsed.append({
            "key": key,
            "weekday": weekday,  # 1=周一, 7=周日
            "period": period,    # 1=1-2节, 2=3-4节, etc.
            "start_period": course.get("KSJC", 0),  # 开始节次
            "end_period": course.get("JSJC", 0),    # 结束节次
            "course_name": course_name,
            "course_name_en": course_name_en,
            "teacher": teacher,
            "weeks": weeks,
            "location": location,
            "period_text": period_text,
            "task_code": course.get("RWH", ""),  # 任务号
            "week_bitmap": course.get("ZC", ""),  # 周次位图
            "training_type": course.get("PYLX", ""),  # 培养类型
            "raw": course,  # 保留原始数据供调试
        })

    return parsed


async def get_schedule_with_dates(
    session: Session,
    xn: str,
    xq: str,
    week: Optional[int] = None,
) -> Dict:
    """获取课表（包含日期信息）"""

    # 并行获取课表和日期
    if week:
        schedule_task = get_week_schedule(session, xn, xq, week)
        dates_task = get_week_dates(session, xn, xq, week)
        schedule, dates = await asyncio.gather(schedule_task, dates_task)
    else:
        schedule = await get_full_schedule(session, xn, xq)
        dates = []

    # 处理日期列表
    date_map = {}
    for date_info in dates:
        xqj = date_info.get("xqj")
        if xqj:
            date_map[int(xqj)] = date_info.get("rq", "")

    return {
        "schedule": schedule,
        "dates": date_map,
        "week": week,
        "term": f"{xn}-{xq}",
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
