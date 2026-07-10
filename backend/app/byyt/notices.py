from typing import Any

from app.byyt.client import BYYTClient
from app.services.session_store import Session


def _notice(item: dict[str, Any]) -> dict[str, Any]:
    external_url = item.get("wburl") or item.get("url")
    return {
        "id": str(item.get("id") or ""),
        "title": str(item.get("bt") or ""),
        "sender": str(item.get("fsr") or ""),
        "sent_at": str(item.get("fssj") or ""),
        "content": str(item.get("nr") or ""),
        "is_read": str(item.get("sfck")) == "1",
        "is_pinned": str(item.get("sfzd")) == "1",
        "has_attachment": bool(item.get("fj")),
        "external_url": str(external_url) if external_url else None,
    }


async def query_notices(session: Session, *, page: int, page_size: int) -> dict[str, Any]:
    result = await BYYTClient(session).request_json(
        "POST",
        "/component/queryTongZhiGongGaoPage",
        data={"pageNum": str(page), "pageSize": str(page_size)},
    )
    result = result if isinstance(result, dict) else {}
    raw_items = result.get("list", [])
    raw_items = raw_items if isinstance(raw_items, list) else []
    return {
        "items": [_notice(item) for item in raw_items if isinstance(item, dict)],
        "page": int(result.get("pageNum") or page),
        "page_size": int(result.get("pageSize") or page_size),
        "total": int(result.get("total") or 0),
    }
