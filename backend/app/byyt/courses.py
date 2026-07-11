import hashlib
import json
from typing import Any

from app.byyt.client import BYYTClient
from app.services.session_store import Session


async def query_selection_term(session: Session, form: bytes) -> dict[str, Any]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/Xsxk/queryXkdqXnxq",
        content=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return result if isinstance(result, dict) else {}


async def query_selected_courses(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    result = await BYYTClient(session).request_json("POST", "/Xsxk/queryYxkc", data=form)
    return result if isinstance(result, dict) else {}


async def query_available_courses(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    fingerprint = hashlib.sha256(json.dumps(form, sort_keys=True, default=str).encode()).hexdigest()
    result = await BYYTClient(session).request_json(
        "POST",
        "/Xsxk/queryKxrw",
        data=form,
        single_flight_key=f"queryKxrw:{fingerprint}",
        cache_ttl=2,
        retry_attempts=2,
    )
    return result if isinstance(result, dict) else {}


async def select_or_add_to_cart(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    result = await BYYTClient(session).request_json("POST", "/Xsxk/addGouwuche", data=form)
    return result if isinstance(result, dict) else {}


async def drop_course(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    result = await BYYTClient(session).request_json("POST", "/Xsxk/tuike", data=form)
    return result if isinstance(result, dict) else {}


async def remove_from_cart(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    result = await BYYTClient(session).request_json("POST", "/Xsxk/delGouwuche", data=form)
    return result if isinstance(result, dict) else {}


async def submit_cart(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    result = await BYYTClient(session).request_json("POST", "/Xsxk/addXuanke", data=form)
    return result if isinstance(result, dict) else {}


async def query_cart(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    result = await BYYTClient(session).request_json("POST", "/Xsxk/queryXkgwc", data=form)
    return result if isinstance(result, dict) else {}


async def query_selection_log(session: Session, form: dict[str, Any]) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/Xsxk/queryXsxkrzList",
        data=form,
    )
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict) and isinstance(result.get("list"), list):
        return [item for item in result["list"] if isinstance(item, dict)]
    return []


async def check_time_conflict(session: Session, form: dict[str, Any]) -> dict[str, Any]:
    result = await BYYTClient(session).request_json("POST", "/Xsxk/cxmtctPd", data=form)
    return result if isinstance(result, dict) else {}


async def query_announcements(
    session: Session,
    *,
    year: str,
    semester: str,
) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/Xsxk/queryXkggZx",
        data={"xn": year, "xq": semester},
        allow_empty=True,
    )
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        items = result.get("list", result.get("content", []))
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    return []


async def query_colleges(session: Session) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/component/queryKkyx",
        content=b"nodataqx=1",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []


async def query_categories(session: Session) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/component/queryKclb",
        data={"pylb": "1"},
        unwrap_content=True,
    )
    return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []


async def query_campuses(session: Session) -> list[dict[str, Any]]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/component/queryXiaoqu",
        params={"pylx": "3"},
        content=b"",
        unwrap_content=True,
    )
    return [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
