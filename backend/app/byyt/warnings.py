from typing import Any, Optional

from app.byyt.client import BYYTClient
from app.services.session_store import Session


def _float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _course(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "course_code": str(item.get("kcdm") or ""),
        "course_name": str(item.get("kcmc") or ""),
        "hours": _float_or_none(item.get("xs")),
        "credits": _float_or_none(item.get("xf")),
        "term": str(item.get("xnxqmc") or ""),
        "score": str(item.get("zzzscj") or ""),
        "course_category": str(item.get("kclbmc") or ""),
        "course_nature": str(item.get("kcxzmc") or ""),
        "exam_attempt": str(item.get("bkcxbj") or ""),
    }


async def query_academic_warnings(
    session: Session,
    *,
    term: Optional[str] = None,
) -> dict[str, Any]:
    client = BYYTClient(session)
    if term:
        year, semester = term.rsplit("-", 1)
    else:
        current = await client.request_json(
            "POST",
            "/xjgl/xyyj/queryXnxq",
            content=b"",
        )
        current = current if isinstance(current, dict) else {}
        year = str(current.get("XN") or "")
        semester = str(current.get("XQ") or "")
        term = f"{year}-{semester}" if year and semester else ""

    result = await client.request_json(
        "POST",
        "/xjgl/xyyj/queryxsXxcj_xs",
        data={"xn": year, "xq": semester},
    )
    result = result if isinstance(result, dict) else {}
    earned = result.get("data_yhd", [])
    earned = earned if isinstance(earned, list) else []
    unearned = result.get("data_whd", [])
    unearned = unearned if isinstance(unearned, list) else []
    acknowledged_at = result.get("hdsj")

    return {
        "term": term,
        "has_warning": str(result.get("sfyyj")) == "1",
        "is_published": str(result.get("sffb")) == "1",
        "is_acknowledged": str(result.get("sfyhd")) == "1",
        "acknowledged_at": str(acknowledged_at) if acknowledged_at else None,
        "counted_credits": _float_or_none(result.get("xf_count")),
        "earned_courses": [_course(item) for item in earned if isinstance(item, dict)],
        "unearned_courses": [_course(item) for item in unearned if isinstance(item, dict)],
    }
