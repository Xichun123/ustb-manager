import re
from typing import Any, Optional

from app.byyt.client import BYYTClient
from app.services.session_store import Session


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _weeks(text: str) -> list[int]:
    odd_only = "单" in text
    even_only = "双" in text
    values: set[int] = set()
    for start, end, single in re.findall(r"(\d+)\s*-\s*(\d+)|(\d+)", text):
        if single:
            values.add(int(single))
        else:
            values.update(range(int(start), int(end) + 1))
    if odd_only:
        values = {value for value in values if value % 2 == 1}
    if even_only:
        values = {value for value in values if value % 2 == 0}
    return sorted(values)


def _weekday(key: str) -> int:
    match = re.match(r"xq([1-7])_jc\d+", key)
    return int(match.group(1)) if match else 0


def _location(text: str) -> tuple[str, str]:
    match = re.match(r"^【([^】]+)】(.*)$", text)
    if not match:
        return "", text
    return match.group(1), match.group(2)


def _course(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    lines = str(item.get("kbxx") or "").splitlines()
    if not lines:
        return None
    english_lines = str(item.get("kbxx_en") or "").splitlines()
    key = str(item.get("key") or "")
    weekday = _weekday(key)
    start_period = _integer(item.get("ksjc"))
    end_period = _integer(item.get("jsjc"))
    if weekday == 0 or start_period == 0 or end_period == 0:
        return None

    course_name = lines[0] if len(lines) > 0 else ""
    teacher = lines[1] if len(lines) > 1 else ""
    week_text = lines[2] if len(lines) > 2 else ""
    location_text = lines[3] if len(lines) > 3 else ""
    period_text = lines[4] if len(lines) > 4 else ""
    campus, location = _location(location_text)

    return {
        "course_id": str(item.get("id") or item.get("rwh") or f"{key}:{course_name}:{week_text}"),
        "course_code": str(item.get("kcdm") or ""),
        "course_name": course_name,
        "course_name_en": english_lines[0] if english_lines else "",
        "teacher": teacher,
        "weekday": weekday,
        "start_period": start_period,
        "end_period": end_period,
        "weeks": _weeks(week_text),
        "week_text": week_text,
        "location": location,
        "campus": campus,
        "period_text": period_text,
        "task_code": str(item.get("rwh") or ""),
    }


async def query_week_options(
    session: Session,
    *,
    year: str | None = None,
    semester: str | None = None,
) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/component/queryzclist",
        data={"xn": year or "", "xq": semester or ""},
    )
    return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []


async def query_schedule(
    session: Session,
    *,
    year: str,
    semester: str,
    week: Optional[int] = None,
) -> dict[str, Any]:
    client = BYYTClient(session)
    raw_items = await client.request_json(
        "POST",
        "/Xskbcx/queryXskbcxList",
        data={
            "sfmrdqxq": "true",
            "xn": year,
            "xq": semester,
            "bs": "2",
            "xskb": "1",
            "bjkb": "0",
            "gwckb": "0",
            "tabs": "1",
            "sfxsgwc": "1",
            "sxbj": "",
        },
    )
    raw_items = raw_items if isinstance(raw_items, list) else []
    items = [course for item in raw_items if isinstance(item, dict) if (course := _course(item))]
    if week is not None:
        items = [course for course in items if not course["weeks"] or week in course["weeks"]]

    dates: dict[int, str] = {}
    if week is not None:
        date_content = await client.request_json(
            "POST",
            "/component/queryRlZcSj",
            data={"xn": year, "xq": semester, "djz": str(week)},
            unwrap_content=True,
        )
        if isinstance(date_content, list):
            for item in date_content:
                if not isinstance(item, dict):
                    continue
                weekday = _integer(item.get("xqj"))
                if weekday:
                    dates[weekday] = str(item.get("rq") or "")

    return {
        "term": f"{year}-{semester}",
        "week": week,
        "dates": dates,
        "items": items,
    }
