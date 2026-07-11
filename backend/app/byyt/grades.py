from typing import Any, Optional

from app.byyt.client import BYYTClient
from app.services.session_store import Session


def _float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _passed(value: Any) -> Optional[bool]:
    if str(value) == "1":
        return True
    if str(value) == "0":
        return False
    return None


def _grade_point(score: float) -> float:
    for minimum, points in (
        (90, 4.0),
        (85, 3.7),
        (82, 3.3),
        (78, 3.0),
        (75, 2.7),
        (72, 2.3),
        (68, 2.0),
        (64, 1.5),
        (60, 1.0),
    ):
        if score >= minimum:
            return points
    return 0.0


def _estimated_gpa(items: list[dict[str, Any]]) -> Optional[float]:
    weighted_points = 0.0
    credits = 0.0
    for item in items:
        score = item.get("score_numeric")
        credit = item.get("credit")
        if item.get("exam_attempt") != "正考" or score is None or not credit:
            continue
        weighted_points += _grade_point(float(score)) * float(credit)
        credits += float(credit)
    return round(weighted_points / credits, 2) if credits else None


def _grade(item: dict[str, Any]) -> dict[str, Any]:
    score = str(item.get("xscj") or "")
    return {
        "id": str(item.get("id") or ""),
        "task_id": str(item.get("rwid") or ""),
        "term": str(item.get("xnxq") or item.get("xnxqmc") or ""),
        "course_code": str(item.get("kcdm") or ""),
        "course_name": str(item.get("kcmc") or ""),
        "course_name_en": str(item.get("kcmc_en") or ""),
        "credit": _float_or_none(item.get("xf")) or 0.0,
        "hours": _float_or_none(item.get("xs")),
        "score": score,
        "score_en": str(item.get("xscjen") or ""),
        "score_numeric": _float_or_none(score),
        "course_nature": str(item.get("kcxz") or ""),
        "course_category": str(item.get("kclb") or ""),
        "college": str(item.get("yxmc") or ""),
        "exam_attempt": str(item.get("bkcx") or ""),
        "passed": _passed(item.get("sfjg")),
        "rank": _int_or_none(item.get("pm")),
        "rank_total": _int_or_none(item.get("zrs")),
    }


async def query_grades(
    session: Session,
    *,
    year: Optional[str] = None,
    semester: Optional[str] = None,
    course_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    content = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/grcjcx/grcjcx",
        json={
            "xn": year,
            "xq": semester,
            "kcmc": course_name,
            "cxbj": "-1",
            "pylx": "1",
            "current": page,
            "pageSize": page_size,
            "xscjlb": None,
            "sffx": None,
        },
        unwrap_content=True,
    )
    content = content if isinstance(content, dict) else {}
    raw_items = content.get("list", [])
    raw_items = raw_items if isinstance(raw_items, list) else []
    return {
        "items": [_grade(item) for item in raw_items if isinstance(item, dict)],
        "page": int(content.get("pageNum") or page),
        "page_size": int(content.get("pageSize") or page_size),
        "total": int(content.get("total") or 0),
    }


async def query_grade_components(
    session: Session,
    *,
    task_id: str,
    grade_id: str,
) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/grcjcx/seeFx",
        data={"rwid": task_id, "cjid": grade_id},
    )
    result = result if isinstance(result, list) else []
    return [
        {
            "name": str(item.get("FXMC") or ""),
            "score": _float_or_none(item.get("DF")),
            "max_score": _float_or_none(item.get("MF")),
            "weight": _float_or_none(item.get("LJFXBZ")),
        }
        for item in result
        if isinstance(item, dict)
    ]


async def query_available_grade_terms(session: Session) -> dict[str, Any]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/queryqxnxq",
        content=b"",
    )
    return result if isinstance(result, dict) else {}


async def query_grade_summary(session: Session) -> dict[str, Any]:
    official = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/grcjcx/getgpa",
        content=b"",
    )
    official = official if isinstance(official, dict) else {}
    grade_page = await query_grades(session, page=1, page_size=1000)
    items = grade_page["items"]

    derived_earned_credits = round(
        sum(float(item["credit"]) for item in items if item.get("passed") is True),
        1,
    )
    derived_passed_courses = sum(item.get("passed") is True for item in items)
    failed_courses = sum(item.get("passed") is False for item in items)

    official_earned_credits = _float_or_none(official.get("HDXF"))
    official_passed_courses = _int_or_none(official.get("TGKC"))
    return {
        "official_gpa": _float_or_none(official.get("GPA")),
        "estimated_gpa": _estimated_gpa(items),
        "earned_credits": (
            official_earned_credits
            if official_earned_credits is not None
            else derived_earned_credits
        ),
        "passed_courses": (
            official_passed_courses
            if official_passed_courses is not None
            else derived_passed_courses
        ),
        "failed_courses": failed_courses,
    }
