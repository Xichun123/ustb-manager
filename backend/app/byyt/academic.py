from datetime import date
from typing import Any

from app.byyt.client import BYYTClient
from app.services.session_store import Session


def _term(year: Any, semester: Any, code: Any = None) -> dict[str, str]:
    year_text = str(year or "")
    semester_text = str(semester or "")
    code_text = str(code or "")
    if not code_text and year_text and semester_text:
        code_text = f"{year_text}-{semester_text}"
    return {
        "year": year_text,
        "semester": semester_text,
        "code": code_text,
    }


async def get_academic_terms(session: Session) -> list[dict[str, Any]]:
    """Return the available academic terms in a stable shape."""
    content = await BYYTClient(session).request_json(
        "POST",
        "/component/queryXnxq",
        content=b"",
        unwrap_content=True,
    )
    content = content if isinstance(content, list) else []
    terms = []
    for item in content:
        if not isinstance(item, dict):
            continue
        term = _term(item.get("xn"), item.get("xq"), item.get("xnxq"))
        terms.append(
            {
                **term,
                "name": str(item.get("xqmc") or ""),
                "name_en": str(item.get("xqmc_en") or ""),
                "is_current": str(item.get("sfdqxq")) == "1",
            }
        )
    return terms


async def get_academic_calendar(
    session: Session,
    *,
    term: str,
    month: int,
) -> dict[str, Any]:
    """Return one calendar month without exposing upstream display flags."""
    year, semester = term.rsplit("-", 1)
    result = await BYYTClient(session).request_json(
        "POST",
        "/Xiaoli/queryMonthList",
        headers={"RoleCode": "01"},
        data={"xn": year, "xq": semester, "yf": str(month)},
    )
    result = result if isinstance(result, dict) else {}

    raw_months = result.get("monlist", [])
    raw_months = raw_months if isinstance(raw_months, list) else []
    month_metadata = next(
        (
            item
            for item in raw_months
            if isinstance(item, dict) and str(item.get("mm")) == str(month)
        ),
        {},
    )

    try:
        calendar_year = int(month_metadata["yy"])
    except (KeyError, TypeError, ValueError):
        calendar_year = None
    try:
        days_in_month = int(month_metadata["dayInMonth"])
    except (KeyError, TypeError, ValueError):
        days_in_month = None

    raw_dates = result.get("xlList", [])
    raw_dates = raw_dates if isinstance(raw_dates, list) else []
    dates = []
    for item in raw_dates:
        if not isinstance(item, dict) or not item.get("RQ"):
            continue
        try:
            item_date = date.fromisoformat(str(item["RQ"]))
        except ValueError:
            continue
        if item_date.month != month or (
            calendar_year is not None and item_date.year != calendar_year
        ):
            continue
        try:
            week = int(item["ZC"]) if item.get("ZC") not in (None, "") else None
        except (TypeError, ValueError):
            week = None
        dates.append({"date": item_date.isoformat(), "week": week})

    return {
        "term": term,
        "month": {
            "year": calendar_year,
            "month": month,
            "label": str(month_metadata.get("ywrq") or ""),
            "days_in_month": days_in_month,
        },
        "dates": dates,
    }


async def get_academic_context(session: Session, on_date: date) -> dict[str, Any]:
    """Return both the administrative term and the date-aware teaching term."""
    client = BYYTClient(session)
    administrative = await client.request_json(
        "POST",
        "/component/querydangqianxnxq",
        content=b"",
    )
    dated_content = await client.request_json(
        "GET",
        "/component/getXnxqByRq",
        params={"rq": on_date.isoformat()},
        unwrap_content=True,
    )

    administrative = administrative if isinstance(administrative, dict) else {}
    dated_content = dated_content if isinstance(dated_content, dict) else {}
    teaching = dated_content.get("rqxnxq", {})
    teaching = teaching if isinstance(teaching, dict) else {}

    try:
        week = int(teaching["zc"]) if teaching.get("zc") not in (None, "") else None
    except (TypeError, ValueError):
        week = None

    teaching_term = _term(teaching.get("xn"), teaching.get("xq"), teaching.get("xnxq"))
    return {
        "date": on_date.isoformat(),
        "administrative_term": _term(
            administrative.get("XN"),
            administrative.get("XQ"),
            administrative.get("XNXQ"),
        ),
        "teaching_term": teaching_term,
        "week": week,
        "is_in_teaching_week": bool(
            teaching_term["year"] and teaching_term["semester"] and week is not None and week > 0
        ),
    }
