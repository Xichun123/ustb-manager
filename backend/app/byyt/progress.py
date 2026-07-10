from typing import Any, Optional

from app.byyt.client import BYYTClient
from app.services.session_store import Session


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
