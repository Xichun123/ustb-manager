import asyncio
from typing import Any, Optional

from app.services import course_service
from app.services.session_store import Session


def _optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> Optional[int]:
    number = _optional_float(value)
    return int(number) if number is not None else None


def _course(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "course_id": str(item.get("task_id") or ""),
        "selection_id": str(item["internal_id"]) if item.get("internal_id") else None,
        "course_code": str(item.get("course_code") or ""),
        "course_name": str(item.get("course_name") or ""),
        "course_name_en": str(item.get("course_name_en") or ""),
        "course_nature": str(item.get("course_type") or ""),
        "course_category": str(item.get("category") or ""),
        "credits": _optional_float(item.get("credits")) or 0,
        "hours": _optional_float(item.get("hours")),
        "method": str(item.get("selection_method_code") or ""),
        "college": str(item.get("college") or ""),
        "campus": str(item.get("campus") or ""),
        "capacity": _optional_int(item.get("capacity")),
        "selected_count": _optional_int(item.get("selected_count")),
        "teacher": str(item.get("teacher") or ""),
        "schedule_time": str(item.get("schedule_time") or ""),
        "schedule_location": str(item.get("schedule_location") or ""),
        "selection_status": str(item.get("selection_status") or ""),
        "is_selected": bool(item.get("is_selected")),
    }


async def _term_params(
    session: Session,
    year: Optional[str] = None,
    semester: Optional[str] = None,
) -> dict[str, str]:
    term = await course_service.get_course_term_info(session)
    selected_year = year or str(term.get("p_xn") or "")
    selected_semester = semester or str(term.get("p_xq") or "")
    return {
        "xn": selected_year,
        "xq": selected_semester,
        "xnxq": (
            f"{selected_year}{selected_semester}"
            if selected_year and selected_semester
            else str(term.get("p_xnxq") or "")
        ),
        "dqxn": str(term.get("p_dqxn") or ""),
        "dqxq": str(term.get("p_dqxq") or ""),
        "dqxnxq": str(term.get("p_dqxnxq") or ""),
    }


async def get_context(session: Session) -> dict[str, Any]:
    context = await course_service.get_course_context(session)
    colleges, categories, campuses = await asyncio.gather(
        course_service.get_colleges(session),
        course_service.get_course_categories(session),
        course_service.get_campuses(session),
    )
    return {
        **context,
        "colleges": colleges,
        "categories": categories,
        "campuses": campuses,
        "capabilities": {
            "course_query": True,
            "selected_query": True,
            "cart_query": True,
            "log_query": True,
            "preflight": True,
            "writes_enabled": False,
        },
    }


async def query_courses(
    session: Session,
    *,
    year: Optional[str],
    semester: Optional[str],
    method: str,
    college: str,
    category: str,
    campus: str,
    keyword: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    params = await _term_params(session, year, semester)
    result = await course_service.get_available_courses(
        session,
        **params,
        xkfsdm=method,
        kkyx=college,
        kclb=category,
        xiaoqu=campus,
        gjz=keyword,
        page_num=page,
        page_size=page_size,
    )
    return {
        "items": [_course(item) for item in result["courses"]],
        "page": page,
        "page_size": page_size,
        "total": int(result["total"]),
        "total_credits": float(result["total_credits"]),
        "method": method,
    }


async def query_selected(
    session: Session,
    *,
    year: Optional[str],
    semester: Optional[str],
) -> dict[str, Any]:
    params = await _term_params(session, year, semester)
    result = await course_service.get_selected_courses(session, **params)
    return {
        "items": [_course(item) for item in result["courses"]],
        "total": int(result["total"]),
        "total_credits": float(result["total_credits"]),
    }


async def query_cart(session: Session, *, method: str) -> dict[str, Any]:
    params = await _term_params(session)
    result = await course_service.get_cart(session, **params, xkfsdm=method)
    return {
        "items": [_course(item) for item in result["courses"]],
        "total": int(result["total"]),
        "total_credits": float(result["total_credits"]),
    }


async def query_logs(session: Session) -> list[dict[str, Any]]:
    params = await _term_params(session)
    items = await course_service.get_selection_log(session, **params)
    return [
        {
            "id": str(item.get("id") or ""),
            "course_code": str(item.get("kcdm") or ""),
            "course_name": str(item.get("kcmc") or ""),
            "operation": str(item.get("czlxmc") or item.get("czlx") or ""),
            "operated_at": str(item.get("czsj") or item.get("cjsj") or ""),
            "status": str(item.get("jg") or ""),
            "message": str(item.get("message") or item.get("msg") or ""),
        }
        for item in items
        if isinstance(item, dict)
    ]
