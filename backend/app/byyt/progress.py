from typing import Any, Optional

from app.byyt.client import BYYTClient
from app.services.session_store import Session


async def query_student_plans(session: Session) -> list[dict[str, Any]]:
    content = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/getXss",
        json={"xjidorxh": session.student_id},
        unwrap_content=True,
    )
    return [item for item in content if isinstance(item, dict)] if isinstance(content, list) else []


async def query_plan_courses(session: Session, plan_id: str) -> list[dict[str, Any]]:
    content = await BYYTClient(session).request_json(
        "POST",
        "/xspyyjsfasq/queryGrjhKcList1",
        data={
            "multiple": "false",
            "pylx": "1",
            "pylb": "1",
            "bgid": "",
            "xsid": "",
            "xh": "",
            "fah": plan_id,
            "kcmcdm": "",
            "yxdm": "",
            "xqdm": "",
            "kclbdm": "",
            "kcxzdm": "",
            "sffaw": "",
            "iskcztpx": "",
            "order1": "",
            "order2": "",
        },
        unwrap_content=True,
    )
    return [item for item in content if isinstance(item, dict)] if isinstance(content, list) else []


async def query_credit_requirement_courses(
    session: Session,
    plan_id: str,
    *,
    page_size: int = 500,
) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/queryXflbyq1",
        json={
            "current": 1,
            "pageSize": page_size,
            "xjid": session.student_id,
            "zyfxdm": None,
            "pylx": "1",
            "fah": plan_id,
        },
    )
    if not isinstance(result, dict) or not isinstance(result.get("xflbyqkc"), list):
        return []
    return [item for item in result["xflbyqkc"] if isinstance(item, dict)]


async def get_student_academic_profile(session: Session) -> dict[str, Any]:
    content = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/getXs",
        json={"xjidorxh": session.student_id, "pylx": "1"},
        unwrap_content=True,
    )
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        raise ValueError("Student academic profile is missing")
    return content[0]


async def query_required_course_status(
    session: Session,
    cutoff_term: Optional[str] = None,
) -> dict[str, Any]:
    profile = await get_student_academic_profile(session)
    content = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/queryBxkqk",
        json={
            "xh": profile.get("xh") or session.student_id or "",
            "pylx": str(profile.get("pylx") or "1"),
            "nj": str(profile.get("nj") or ""),
            "jzxnxq": cutoff_term or "",
            "xjid": str(profile.get("xjid") or profile.get("id") or ""),
            "zyfxdm": str(profile.get("zyfxdm") or ""),
            "fah": str(profile.get("fah") or ""),
        },
        unwrap_content=True,
    )
    return content if isinstance(content, dict) else {}


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


def _optional_bool_flag(value: Any) -> Optional[bool]:
    if str(value) not in {"0", "1"}:
        return None
    return str(value) == "1"


def _first_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if item.get(key) not in (None, ""):
            return item[key]
    return None


def _normalize_module(item: dict[str, Any]) -> dict[str, Any]:
    children = item.get("children") if isinstance(item.get("children"), list) else []
    return {
        "id": str(item.get("kzid") or ""),
        "parent_id": str(item.get("fkzid") or ""),
        "name": str(item.get("title") or item.get("kzmc") or ""),
        "name_en": str(item.get("kzmc_en") or ""),
        "module_type": str(item.get("kzlx") or ""),
        "course_category_code": str(item.get("kclbdm") or ""),
        "course_nature_code": str(item.get("kcxzdm") or ""),
        "required_groups": _optional_int(item.get("yqxdkzs")),
        "completed_groups": _optional_int(item.get("wc_kzsl")),
        "required_courses": _optional_int(item.get("yqxdms")),
        "completed_courses": _optional_int(item.get("wc_ms")),
        "required_hours": _optional_float(item.get("yqxdxs")),
        "completed_hours": _optional_float(item.get("wc_xs")),
        "required_credits": _optional_float(item.get("yqxdxf")),
        "completed_credits": _optional_float(item.get("wc_xf")),
        "passed": _optional_bool_flag(item.get("sftg")),
        "is_required": _optional_bool_flag(item.get("sfbx")),
        "remark": str(item.get("bz") or ""),
        "children": [_normalize_module(child) for child in children if isinstance(child, dict)],
    }


async def query_academic_progress(
    session: Session,
    cutoff_term: Optional[str] = None,
) -> dict[str, Any]:
    if cutoff_term:
        year, semester = cutoff_term.rsplit("-", 1)
        upstream_term = f"{year}{semester}"
    else:
        upstream_term = None
    status = await query_required_course_status(session, upstream_term)
    requirements = status.get("yqmsxf") if isinstance(status.get("yqmsxf"), dict) else {}
    return {
        "cutoff_term": cutoff_term,
        "required_courses": _optional_int(requirements.get("YQMS")),
        "completed_courses": _optional_int(status.get("ywcms")),
        "remaining_courses": _optional_int(status.get("wwcms")),
        "required_credits": _optional_float(requirements.get("YQXF")),
        "completed_credits": _optional_float(status.get("ywcxf")),
        "remaining_credits": _optional_float(status.get("wwcxf")),
        "credit_score": _optional_float(requirements.get("XFJ")),
        "major_rank": _optional_int(requirements.get("PM")),
        "major_student_count": _optional_int(requirements.get("ZYRS")),
    }


async def query_academic_progress_modules(session: Session) -> dict[str, Any]:
    profile = await get_student_academic_profile(session)
    content = await BYYTClient(session).request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/queryMkyq",
        json={
            "xjid": str(profile.get("xjid") or profile.get("id") or ""),
            "zyfxdm": str(profile.get("zyfxdm") or ""),
            "fah": str(profile.get("fah") or ""),
            "pylx": str(profile.get("pylx") or "1"),
        },
        unwrap_content=True,
    )
    items = content if isinstance(content, list) else []
    normalized = [_normalize_module(item) for item in items if isinstance(item, dict)]
    return {"is_available": bool(normalized), "items": normalized}


def _normalize_category(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(item.get("kclbdm") or ""),
        "name": str(item.get("kclbmc") or ""),
        "name_en": str(item.get("kclbmc_en") or ""),
        "course_nature_code": str(item.get("kcxzdm") or ""),
        "course_nature": str(item.get("kcxzmc") or ""),
        "required_credits": _optional_float(item.get("yqwcxf")),
        "completed_credits": _optional_float(item.get("ywcxf")),
        "remaining_credits": _optional_float(item.get("wwcxf")),
        "convertible_credits": _optional_float(item.get("kzhxf")),
        "converted_credits": _optional_float(item.get("yzhxf")),
        "remark": str(item.get("bz") or ""),
    }


def _is_course_row(item: dict[str, Any]) -> bool:
    return bool(str(item.get("kcdm") or "").strip() or str(item.get("kcmc") or "").strip())


def _normalize_course(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(_first_value(item, "id", "kcid", "kcdm") or ""),
        "course_code": str(item.get("kcdm") or ""),
        "course_name": str(item.get("kcmc") or ""),
        "course_name_en": str(item.get("kcmc_en") or ""),
        "term": str(_first_value(item, "xnxqmc", "tjkkxnxq") or ""),
        "credits": _optional_float(item.get("xf")),
        "hours": _optional_float(_first_value(item, "xs", "sjzxs")),
        "score": str(_first_value(item, "xscj", "zzcj", "cj") or ""),
        "passed": _optional_bool_flag(item.get("sftg")),
        "counts_toward_requirement": _optional_bool_flag(item.get("sfyxkc")),
        "is_required": _optional_bool_flag(item.get("sfbx")),
        "course_nature_code": str(item.get("kcxzdm") or ""),
        "course_nature": str(item.get("kcxzmc") or ""),
        "course_category_code": str(item.get("kclbdm") or ""),
        "course_category": str(item.get("kclbmc") or ""),
        "college": str(item.get("kkyxmc") or ""),
        "module_id": str(item.get("kzid") or ""),
        "module_name": str(item.get("kzmc") or ""),
        "major_direction_code": str(item.get("zyfxdm") or ""),
        "major_direction": str(item.get("zyfxmc") or ""),
    }


async def query_academic_progress_courses(session: Session) -> dict[str, Any]:
    profile = await get_student_academic_profile(session)
    params = {
        "current": 1,
        "pageSize": 500,
        "xjid": str(profile.get("xjid") or profile.get("id") or ""),
        "zyfxdm": str(profile.get("zyfxdm") or ""),
        "pylx": str(profile.get("pylx") or "1"),
        "fah": str(profile.get("fah") or ""),
    }
    client = BYYTClient(session)
    visibility = await client.request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/querysfxsxflbyq",
        json=params,
    )
    visible_value = _optional_float(visibility)
    if visible_value is None or visible_value <= 0:
        return {"is_available": False, "categories": [], "courses": []}

    result = await client.request_json(
        "POST",
        "/cjgl/cjzhtjcx/cjcx/queryXflbyq1",
        json=params,
    )
    if not isinstance(result, dict):
        return {"is_available": True, "categories": [], "courses": []}
    raw_categories = result.get("xflbyq") if isinstance(result.get("xflbyq"), list) else []
    raw_courses = result.get("xflbyqkc") if isinstance(result.get("xflbyqkc"), list) else []
    return {
        "is_available": True,
        "categories": [
            _normalize_category(item) for item in raw_categories if isinstance(item, dict)
        ],
        "courses": [
            _normalize_course(item)
            for item in raw_courses
            if isinstance(item, dict) and _is_course_row(item)
        ],
    }
