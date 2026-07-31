import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, Optional

from app.byyt.errors import BYYTRateLimited, BYYTUnavailable, BYYTUpstreamError
from app.exceptions import (
    BYYTSessionExpired,
    CourseConflict,
    CourseOperationBlocked,
    IdempotencyKeyReused,
)
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
        "internal_capacity": _optional_int(item.get("internal_capacity")),
        "internal_selected_count": _optional_int(item.get("internal_selected_count")),
        "external_capacity": _optional_int(item.get("external_capacity")),
        "external_selected_count": _optional_int(item.get("external_selected_count")),
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
    facing: str,
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
        sfmxzj=facing,
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
    selection_id: Optional[str] = None,
    method: str,
) -> dict[str, Any]:
    params = await _term_params(session)
    result = await course_service.check_time_conflict(
        session,
        **params,
        course_id=selection_id or course_id,
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
        error_type = str(result.get("error_type") or "unknown")
        if error_type == "conflict":
            raise CourseConflict(message)
        error_details = {
            "full": ("COURSE_FULL", True),
            "not_open": ("COURSE_NOT_OPEN", True),
            "not_eligible": ("COURSE_NOT_ELIGIBLE", False),
            "already_selected": ("COURSE_ALREADY_SELECTED", False),
        }.get(error_type, ("COURSE_OPERATION_BLOCKED", False))
        raise CourseOperationBlocked(
            message,
            code=error_details[0],
            retryable=error_details[1],
        )
    return {"success": True, "status": "success", "message": message}


async def _is_course_selected(
    session: Session,
    *,
    params: dict[str, str],
    course_id: str,
) -> bool:
    selected = await course_service.get_selected_courses(session, **params)
    return any(item.get("task_id") == course_id for item in selected["courses"])


async def create_selection(
    session: Session,
    *,
    course_id: str,
    selection_id: Optional[str] = None,
    method: str,
    idempotency_key: str,
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        params = await _term_params(session)
        upstream_id = selection_id or course_id
        result = await course_service.select_course(
            session, **params, course_id=upstream_id, xkfsdm=method
        )
        if selection_id and not result["success"] and result.get("error_type") == "unknown":
            conflict = await course_service.check_time_conflict(
                session,
                **params,
                course_id=upstream_id,
                xkfsdm=method,
            )
            if conflict["status"] == "conflict":
                result = {
                    **result,
                    "error_type": "conflict",
                    "message": conflict["message"] or result["message"],
                }
        if result.get("error_type") == "already_selected" and await _is_course_selected(
            session,
            params=params,
            course_id=course_id,
        ):
            return {
                "success": True,
                "status": "success",
                "message": result.get("message") or "课程已在已选列表中",
            }
        return _successful_write(result)

    return await _execute_idempotent(
        session,
        operation="select",
        key=idempotency_key,
        fingerprint=f"{course_id}:{selection_id or ''}:{method}",
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
    selection_id: Optional[str] = None,
    method: str,
    idempotency_key: str,
) -> dict[str, Any]:
    async def execute() -> dict[str, Any]:
        params = await _term_params(session)
        upstream_id = selection_id or course_id
        result = await course_service.check_time_conflict(
            session, **params, course_id=upstream_id, xkfsdm=method
        )
        _require_clear_preflight(result)
        return _successful_write(
            await course_service.add_to_cart(
                session,
                **params,
                course_id=upstream_id,
                xkfsdm=method,
            )
        )

    return await _execute_idempotent(
        session,
        operation="cart-add",
        key=idempotency_key,
        fingerprint=f"{course_id}:{selection_id or ''}:{method}",
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _snatch_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: ([dict(item) for item in value] if key == "items" else value)
        for key, value in state.items()
    }


async def _finish_snatch_task(
    session: Session,
    task_id: str,
    *,
    status: str,
    message: str = "",
) -> None:
    async with session.course_snatch_lock:
        state = session.course_snatch_tasks[task_id]
        state["status"] = status
        state["message"] = message
        state["finished_at"] = _utc_now()


async def _run_snatch_task(session: Session, task_id: str) -> None:
    try:
        async with session.course_snatch_lock:
            state = session.course_snatch_tasks[task_id]
            start_at = state["start_at"]
        delay = max(0.0, (start_at - _utc_now()).total_seconds())
        if delay:
            await asyncio.sleep(delay)

        async with session.course_snatch_lock:
            state = session.course_snatch_tasks[task_id]
            state["status"] = "running"
            state["started_at"] = _utc_now()
            retry_interval = float(state["retry_interval_seconds"])

        params = await _term_params(session)
        while True:
            async with session.course_snatch_lock:
                state = session.course_snatch_tasks[task_id]
                remaining_indexes = [
                    index
                    for index, item in enumerate(state["items"])
                    if item["status"] in {"pending", "retrying"}
                ]

            if not remaining_indexes:
                async with session.course_snatch_lock:
                    items = session.course_snatch_tasks[task_id]["items"]
                    has_failures = any(item["status"] == "failed" for item in items)
                await _finish_snatch_task(
                    session,
                    task_id,
                    status="completed_with_errors" if has_failures else "completed",
                )
                return

            for position, index in enumerate(remaining_indexes):
                async with session.course_snatch_lock:
                    item = session.course_snatch_tasks[task_id]["items"][index]
                    item["status"] = "retrying"
                    item["attempts"] += 1
                    item["error_type"] = None
                    course_id = item["course_id"]
                    selection_id = item.get("selection_id")
                    upstream_id = selection_id or course_id
                    method = item["method"]

                try:
                    # 直接选课接口会自行校验冲突；cxmtctPd 仅用于购物车预检。
                    result = await course_service.select_course(
                        session,
                        **params,
                        course_id=upstream_id,
                        xkfsdm=method,
                    )
                    if (
                        selection_id
                        and not result["success"]
                        and result.get("error_type") == "unknown"
                    ):
                        conflict = await course_service.check_time_conflict(
                            session,
                            **params,
                            course_id=upstream_id,
                            xkfsdm=method,
                        )
                        if conflict["status"] == "conflict":
                            result = {
                                **result,
                                "error_type": "conflict",
                                "message": conflict["message"] or result["message"],
                            }
                    async with session.course_snatch_lock:
                        item = session.course_snatch_tasks[task_id]["items"][index]
                        error_type = result.get("error_type")
                        already_selected = error_type == "already_selected"

                    confirmed_selected = already_selected and await _is_course_selected(
                        session,
                        params=params,
                        course_id=course_id,
                    )

                    async with session.course_snatch_lock:
                        item = session.course_snatch_tasks[task_id]["items"][index]
                        if result["success"] or confirmed_selected:
                            item["status"] = "success"
                            item["message"] = result["message"] or "选课成功"
                            item["error_type"] = None
                        elif error_type in {"conflict", "not_eligible"}:
                            item["status"] = "failed"
                            item["message"] = result["message"] or "课程不可选择"
                            item["error_type"] = error_type
                        else:
                            item["message"] = result["message"] or "暂未成功，等待重试"
                            item["error_type"] = error_type or "unknown"
                except (BYYTRateLimited, BYYTUnavailable, BYYTUpstreamError):
                    async with session.course_snatch_lock:
                        session.course_snatch_tasks[task_id]["items"][index]["message"] = (
                            "教务系统繁忙，正在退避重试"
                        )
                except BYYTSessionExpired:
                    await _finish_snatch_task(
                        session,
                        task_id,
                        status="failed",
                        message="教务系统登录已过期，请重新登录",
                    )
                    return

                if position + 1 < len(remaining_indexes):
                    await asyncio.sleep(min(1.0, retry_interval))

            await asyncio.sleep(retry_interval)
    except asyncio.CancelledError:
        async with session.course_snatch_lock:
            state = session.course_snatch_tasks.get(task_id)
            if state and state["status"] not in {"completed", "completed_with_errors", "failed"}:
                state["status"] = "stopped"
                state["message"] = "任务已手动停止"
                state["finished_at"] = _utc_now()
        raise
    except Exception:
        await _finish_snatch_task(
            session,
            task_id,
            status="failed",
            message="抢课任务异常终止",
        )


async def create_snatch_task(
    session: Session,
    *,
    courses: list[dict[str, str]],
    start_at: datetime,
    retry_interval_seconds: float,
    idempotency_key: str,
) -> dict[str, Any]:
    fingerprint = json.dumps(
        {
            "courses": courses,
            "start_at": start_at.isoformat(),
            "retry_interval_seconds": retry_interval_seconds,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    async def execute() -> dict[str, Any]:
        async with session.course_snatch_lock:
            active = next(
                (
                    state
                    for state in session.course_snatch_tasks.values()
                    if state["status"] in {"scheduled", "running"}
                ),
                None,
            )
            if active:
                raise CourseOperationBlocked("已有进行中的抢课任务，请先停止")

            task_id = uuid.uuid4().hex
            state = {
                "task_id": task_id,
                "status": "scheduled",
                "start_at": start_at.astimezone(timezone.utc),
                "retry_interval_seconds": retry_interval_seconds,
                "created_at": _utc_now(),
                "started_at": None,
                "finished_at": None,
                "message": "",
                "items": [
                    {
                        **course,
                        "status": "pending",
                        "attempts": 0,
                        "message": "",
                        "error_type": None,
                    }
                    for course in courses
                ],
            }
            session.course_snatch_tasks[task_id] = state
            runner = asyncio.create_task(_run_snatch_task(session, task_id))
            session.course_snatch_runners[task_id] = runner
            runner.add_done_callback(lambda _: session.course_snatch_runners.pop(task_id, None))
            return _snatch_snapshot(state)

    return await _execute_idempotent(
        session,
        operation="snatch-create",
        key=idempotency_key,
        fingerprint=fingerprint,
        execute=execute,
    )


async def get_active_snatch_task(session: Session) -> Optional[dict[str, Any]]:
    async with session.course_snatch_lock:
        state = next(
            (
                task
                for task in reversed(session.course_snatch_tasks.values())
                if task["status"] in {"scheduled", "running"}
            ),
            None,
        )
        return _snatch_snapshot(state) if state else None


async def get_snatch_task(session: Session, task_id: str) -> Optional[dict[str, Any]]:
    async with session.course_snatch_lock:
        state = session.course_snatch_tasks.get(task_id)
        return _snatch_snapshot(state) if state else None


async def stop_snatch_task(session: Session, task_id: str) -> Optional[dict[str, Any]]:
    async with session.course_snatch_lock:
        state = session.course_snatch_tasks.get(task_id)
        if state is None:
            return None
        if state["status"] not in {"completed", "completed_with_errors", "stopped", "failed"}:
            state["status"] = "stopped"
            state["message"] = "任务已手动停止"
            state["finished_at"] = _utc_now()
        runner = session.course_snatch_runners.get(task_id)

    if runner and not runner.done():
        runner.cancel()
        try:
            await runner
        except asyncio.CancelledError:
            pass

    return await get_snatch_task(session, task_id)


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
