import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from app.exceptions import CourseConflict, CourseOperationBlocked, IdempotencyKeyReused
from app.services import course_service
from app.services.session_store import Session


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


def _course(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "course_id": str(item.get("task_id") or ""),
        "selection_id": str(item["internal_id"]) if item.get("internal_id") else None,
        "course_code": str(item.get("course_code") or ""),
        "course_name": str(item.get("course_name") or ""),
        "course_name_en": str(item.get("course_name_en") or ""),
        "course_nature": str(item.get("course_type") or ""),
        "course_category": str(item.get("category") or ""),
        "credits": _optional_float(item.get("credits")) or 0,
        "hours": _optional_float(item.get("hours")),
        "method": str(item.get("selection_method_code") or ""),
        "college": str(item.get("college") or ""),
        "campus": str(item.get("campus") or ""),
        "capacity": _optional_int(item.get("capacity")),
        "selected_count": _optional_int(item.get("selected_count")),
        "teacher": str(item.get("teacher") or ""),
        "schedule_time": str(item.get("schedule_time") or ""),
        "schedule_location": str(item.get("schedule_location") or ""),
        "selection_status": str(item.get("selection_status") or ""),
        "is_selected": bool(item.get("is_selected")),
    }


async def _term_params(
    session: Session,
    year: Optional[str] = None,
    semester: Optional[str] = None,
) -> dict[str, str]:
    term = await course_service.get_course_term_info(session)
    selected_year = year or str(term.get("p_xn") or "")
    selected_semester = semester or str(term.get("p_xq") or "")
    return {
        "xn": selected_year,
        "xq": selected_semester,
        "xnxq": (
            f"{selected_year}{selected_semester}"
            if selected_year and selected_semester
            else str(term.get("p_xnxq") or "")
        ),
        "dqxn": str(term.get("p_dqxn") or ""),
        "dqxq": str(term.get("p_dqxq") or ""),
        "dqxnxq": str(term.get("p_dqxnxq") or ""),
    }


async def get_context(session: Session) -> dict[str, Any]:
    context = await course_service.get_course_context(session)
    colleges, categories, campuses = await asyncio.gather(
        course_service.get_colleges(session),
        course_service.get_course_categories(session),
        course_service.get_campuses(session),
    )
    return {
        **context,
        "colleges": colleges,
        "categories": categories,
        "campuses": campuses,
        "capabilities": {
            "course_query": True,
            "selected_query": True,
            "cart_query": True,
            "log_query": True,
            "preflight": True,
            "writes_enabled": True,
        },
    }


async def query_courses(
    session: Session,
    *,
    year: Optional[str],
    semester: Optional[str],
    method: str,
    college: str,
    category: str,
    campus: str,
    keyword: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    params = await _term_params(session, year, semester)
    result = await course_service.get_available_courses(
        session,
        **params,
        xkfsdm=method,
        kkyx=college,
        kclb=category,
        xiaoqu=campus,
        gjz=keyword,
        page_num=page,
        page_size=page_size,
    )
    return {
        "items": [_course(item) for item in result["courses"]],
        "page": page,
        "page_size": page_size,
        "total": int(result["total"]),
        "total_credits": float(result["total_credits"]),
        "method": method,
    }


async def query_selected(
    session: Session,
    *,
    year: Optional[str],
    semester: Optional[str],
) -> dict[str, Any]:
    params = await _term_params(session, year, semester)
    result = await course_service.get_selected_courses(session, **params)
    return {
        "items": [_course(item) for item in result["courses"]],
        "total": int(result["total"]),
        "total_credits": float(result["total_credits"]),
    }


async def query_cart(session: Session, *, method: str) -> dict[str, Any]:
    params = await _term_params(session)
    result = await course_service.get_cart(session, **params, xkfsdm=method)
    return {
        "items": [_course(item) for item in result["courses"]],
        "total": int(result["total"]),
        "total_credits": float(result["total_credits"]),
    }


async def preflight(
    session: Session,
    *,
    course_id: str,
    method: str,
) -> dict[str, Any]:
    params = await _term_params(session)
    result = await course_service.check_time_conflict(
        session,
        **params,
        course_id=course_id,
        xkfsdm=method,
    )
    return {
        "allowed": result["allowed"],
        "status": result["status"],
        "message": result["message"],
    }


async def _execute_idempotent(
    session: Session,
    *,
    operation: str,
    key: str,
    fingerprint: str,
    execute: Callable[[], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    cache_key = f"{operation}:{key}"
    async with session.idempotency_lock:
        cached = session.idempotency_results.get(cache_key)
        if cached is not None:
            cached_fingerprint, cached_result = cached
            if cached_fingerprint != fingerprint:
                raise IdempotencyKeyReused
            return cached_result
        result = await execute()
        if len(session.idempotency_results) >= 100:
            session.idempotency_results.pop(next(iter(session.idempotency_results)))
        session.idempotency_results[cache_key] = (fingerprint, result)
        return result


def _successful_write(result: dict[str, Any]) -> dict[str, Any]:
    message = str(result.get("message") or "")
    if not result.get("success"):
        raise CourseOperationBlocked(message)
    return {"success": True, "status": "success", "message": message}


async def create_selection(
    session: Session,
    *,
    course_id: str,
    method: str,
    idempotency_key: str,
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        params = await _term_params(session)
        result = await course_service.check_time_conflict(
            session, **params, course_id=course_id, xkfsdm=method
        )
        _require_clear_preflight(result)
        return _successful_write(
            await course_service.select_course(
                session, **params, course_id=course_id, xkfsdm=method
            )
        )

    return await _execute_idempotent(
        session,
        operation="select",
        key=idempotency_key,
        fingerprint=f"{course_id}:{method}",
        execute=execute,
    )


async def delete_selection(
    session: Session,
    *,
    selection_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        params = await _term_params(session)
        return _successful_write(
            await course_service.drop_course(session, **params, course_id=selection_id)
        )

    return await _execute_idempotent(
        session,
        operation="drop",
        key=idempotency_key,
        fingerprint=selection_id,
        execute=execute,
    )


async def add_cart_item(
    session: Session,
    *,
    course_id: str,
    method: str,
    idempotency_key: str,
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        params = await _term_params(session)
        result = await course_service.check_time_conflict(
            session, **params, course_id=course_id, xkfsdm=method
        )
        _require_clear_preflight(result)
        return _successful_write(
            await course_service.add_to_cart(session, **params, course_id=course_id, xkfsdm=method)
        )

    return await _execute_idempotent(
        session,
        operation="cart-add",
        key=idempotency_key,
        fingerprint=f"{course_id}:{method}",
        execute=execute,
    )


async def delete_cart_items(
    session: Session,
    *,
    item_ids: list[str],
    method: str,
    idempotency_key: str,
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        params = await _term_params(session)
        return _successful_write(
            await course_service.remove_from_cart(
                session,
                **params,
                course_ids=item_ids,
                xkfsdm=method,
            )
        )

    return await _execute_idempotent(
        session,
        operation="cart-remove",
        key=idempotency_key,
        fingerprint=f"{','.join(item_ids)}:{method}",
        execute=execute,
    )


async def delete_cart_item(
    session: Session,
    *,
    item_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    return await delete_cart_items(
        session,
        item_ids=[item_id],
        method="bx-b-b",
        idempotency_key=idempotency_key,
    )


async def submit_cart(
    session: Session,
    *,
    method: str = "bx-b-b",
    idempotency_key: str,
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        params = await _term_params(session)
        return _successful_write(await course_service.submit_cart(session, **params, xkfsdm=method))

    return await _execute_idempotent(
        session,
        operation="cart-submit",
        key=idempotency_key,
        fingerprint=method,
        execute=execute,
    )


def _require_clear_preflight(result: dict[str, Any]) -> None:
    if result["allowed"]:
        return
    if result["status"] == "conflict":
        raise CourseConflict(result["message"])
    raise CourseOperationBlocked(result["message"])


async def query_announcements(session: Session) -> list[dict[str, Any]]:
    params = await _term_params(session)
    items = await course_service.get_announcements(
        session,
        xn=params["xn"],
        xq=params["xq"],
    )
    return [
        {
            "id": str(item.get("id") or item.get("ggid") or ""),
            "title": str(item.get("ggbt") or item.get("ggmc") or item.get("title") or ""),
            "content": str(item.get("ggnr") or item.get("content") or ""),
            "published_at": str(item.get("fbsj") or item.get("cjsj") or ""),
        }
        for item in items
        if isinstance(item, dict)
    ]


async def query_logs(session: Session) -> list[dict[str, Any]]:
    params = await _term_params(session)
    items = await course_service.get_selection_log(session, **params)
    return [
        {
            "id": str(item.get("id") or ""),
            "course_code": str(item.get("kcdm") or ""),
            "course_name": str(item.get("kcmc") or ""),
            "operation": str(item.get("czlxmc") or item.get("czlx") or ""),
            "operated_at": str(item.get("czsj") or item.get("cjsj") or ""),
            "status": str(item.get("jg") or ""),
            "message": str(item.get("message") or item.get("msg") or ""),
        }
        for item in items
        if isinstance(item, dict)
    ]
