from typing import Any, Optional

from app.byyt.client import BYYTClient
from app.services.session_store import Session


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _exam(item: dict[str, Any]) -> dict[str, Any]:
    year = str(item.get("XN") or "")
    semester = str(item.get("XQ") or "")
    term = f"{year}-{semester}" if year and semester else ""
    seat_number = item.get("ZWH")
    return {
        "id": str(item.get("ROW_ID") or item.get("KSHKID") or item.get("KSBH") or ""),
        "term": term,
        "course_code": str(item.get("KCDM") or ""),
        "course_name": str(item.get("KCMC") or ""),
        "course_name_en": str(item.get("KCMC_EN") or ""),
        "exam_type": str(item.get("KSSJDMC") or ""),
        "exam_type_en": str(item.get("KSSJDMC_EN") or ""),
        "date": str(item.get("KSRQ") or ""),
        "date_display": str(item.get("KSRQ2") or ""),
        "time": str(item.get("KSJTSJ") or ""),
        "week": _int_or_none(item.get("DJZ")),
        "weekday": _int_or_none(item.get("XQJ")),
        "weekday_name": str(item.get("XQJMC") or ""),
        "start_period": _int_or_none(item.get("KSJC")),
        "end_period": _int_or_none(item.get("JSJC")),
        "building": str(item.get("JXLMC") or ""),
        "room": str(item.get("CDMC") or item.get("JXCDMC") or ""),
        "seat_number": str(seat_number) if seat_number not in (None, "") else None,
        "college": str(item.get("KKYXMC") or ""),
        "remark": str(item.get("JKJSBZ") or ""),
    }


async def query_exams(
    session: Session,
    *,
    year: str,
    semester: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/kscxtj/queryXsksByxhList",
        data={
            "ppylx": "1",
            "pxn": year,
            "pxq": semester,
            "pkssjdm": "",
            "pkkyx": "",
            "pageNum": str(page),
            "pageSize": str(page_size),
        },
    )
    result = result if isinstance(result, dict) else {}
    raw_items = result.get("list", [])
    raw_items = raw_items if isinstance(raw_items, list) else []
    return {
        "items": [_exam(item) for item in raw_items if isinstance(item, dict)],
        "page": int(result.get("pageNum") or page),
        "page_size": int(result.get("pageSize") or page_size),
        "total": int(result.get("total") or 0),
    }
