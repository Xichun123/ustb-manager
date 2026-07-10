from typing import Any

from app.byyt.client import BYYTClient
from app.services.session_store import Session


def _student_content(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    content = result.get("content")
    if isinstance(content, dict):
        return content
    if isinstance(content, list) and content and isinstance(content[0], dict):
        return content[0]
    return result


def _optional_text(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


async def get_user_profile(session: Session) -> dict[str, Any]:
    client = BYYTClient(session)
    student_result = await client.request_json(
        "POST",
        "/UserManager/queryxsxx",
        content=b"",
    )
    user_result = await client.request_json(
        "POST",
        "/user/me",
        content=b"",
    )
    student = _student_content(student_result)
    user = user_result if isinstance(user_result, dict) else {}

    raw_roles = user.get("role", [])
    raw_roles = raw_roles if isinstance(raw_roles, list) else []
    roles = [
        {
            "code": str(item.get("jsdm") or ""),
            "name": str(item.get("jsmc") or ""),
            "name_en": str(item.get("jsmc_en") or ""),
        }
        for item in raw_roles
        if isinstance(item, dict) and item.get("jsdm")
    ]

    return {
        "student_id": str(student.get("XH") or user.get("userId") or session.student_id or ""),
        "name": str(student.get("XM") or user.get("xm") or ""),
        "name_en": str(student.get("XM_EN") or user.get("xm_en") or ""),
        "college": str(student.get("YXMC") or user.get("bmmc") or ""),
        "college_en": str(student.get("YXMC_EN") or user.get("bmmc_en") or ""),
        "major": str(student.get("ZYMC") or ""),
        "major_en": str(student.get("ZYMC_EN") or ""),
        "class_name": str(student.get("BJMC") or ""),
        "class_name_en": str(student.get("BJMC_EN") or ""),
        "grade": str(student.get("NJMC") or ""),
        "grade_en": str(student.get("NJMC_EN") or ""),
        "email": _optional_text(student.get("DZYX")),
        "phone": _optional_text(student.get("LXDH")),
        "photo_url": _optional_text(student.get("ZPBSLJ")),
        "training_type": str(student.get("PYLX") or user.get("pylx") or ""),
        "roles": roles,
    }
