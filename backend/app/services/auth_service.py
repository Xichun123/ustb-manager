import asyncio
import logging
from typing import AsyncGenerator

from ustb_sso import HttpxSession, QrAuthProcedure, SmsAuthProcedure, exceptions, prefabs

from app.byyt.profile import get_student_identity

from .session_store import AuthState, Session, store

logger = logging.getLogger(__name__)

_IDENTITY_ATTEMPTS = 3
_IDENTITY_RETRY_DELAY = 1


def _byyt_cookies(session: Session) -> dict[str, str]:
    return {
        cookie.name: cookie.value
        for cookie in session.client.cookies.jar
        if "ustb.edu.cn" in cookie.domain
    }


async def _activate_authenticated_session(session: Session, flow: str) -> None:
    for attempt in range(_IDENTITY_ATTEMPTS):
        try:
            identity = await get_student_identity(session)
            break
        except Exception as exc:
            logger.warning(
                "%s student identity lookup failed, attempt %s/%s: %s",
                flow,
                attempt + 1,
                _IDENTITY_ATTEMPTS,
                type(exc).__name__,
            )
            if attempt == _IDENTITY_ATTEMPTS - 1:
                raise
            await asyncio.sleep(_IDENTITY_RETRY_DELAY)

    cookies = _byyt_cookies(session)
    if cookies and session.session_id:
        store.persist(session.session_id, identity.student_id, cookies)

    async with session.lock:
        session.state = AuthState.ACTIVE
        session.authenticated = True
        session.student_id = identity.student_id


async def _claim_qr_monitor(session: Session) -> tuple[QrAuthProcedure | None, str | None]:
    async with session.lock:
        proc: QrAuthProcedure = session.procedure
        if not proc or session.state != AuthState.QR_READY:
            return None, "invalid"
        if session.qr_monitor_started:
            return None, "active"
        session.qr_monitor_started = True
        session.last_error = None
        return proc, None


async def _release_qr_monitor(session: Session) -> None:
    async with session.lock:
        session.qr_monitor_started = False


async def init_qr_auth(session: Session) -> bytes:
    def _sync():
        sso_session = HttpxSession(session.client)
        proc = QrAuthProcedure(**prefabs.BYYT_USTB_EDU_CN, session=sso_session)
        proc.open_auth()
        proc.use_wechat_auth().use_qr_code()
        qr_bytes = proc.get_qr_image()
        return proc, qr_bytes

    async with session.lock:
        proc, qr_bytes = await asyncio.to_thread(_sync)
        session.procedure = proc
        session.state = AuthState.QR_READY
        session.qr_image = qr_bytes
        session.last_error = None
        session.qr_monitor_started = False
    return qr_bytes


async def start_qr_background_monitor(session: Session):
    """Start QR monitoring in background for polling-based clients (mini program)."""
    proc, reason = await _claim_qr_monitor(session)
    if reason is not None:
        return

    async def _monitor():
        try:

            def _poll():
                try:
                    return proc.wait_for_pass_code()
                except exceptions.TimeoutError:
                    return None

            pass_code = await asyncio.to_thread(_poll)
            if pass_code is None:
                async with session.lock:
                    session.state = AuthState.EXPIRED
                    session.last_error = None
                return

            async with session.lock:
                session.state = AuthState.CONFIRMED
                session.last_error = None

            await asyncio.to_thread(proc.complete_auth, pass_code)
            await _activate_authenticated_session(session, "QR")
            logger.info("QR background monitor completed")
        except Exception as exc:
            logger.error("QR background monitor failed: %s", type(exc).__name__)
            async with session.lock:
                session.last_error = "QR login failed"
        finally:
            await _release_qr_monitor(session)

    asyncio.create_task(_monitor())


async def poll_qr_status(session: Session) -> AsyncGenerator[dict, None]:
    logger.info("poll_qr_status started, state=%s", session.state)
    proc, reason = await _claim_qr_monitor(session)
    if reason == "active":
        logger.error("QR status polling rejected because another monitor is active")
        yield {"status": "error", "message": "Invalid state"}
        return
    if reason is not None:
        logger.error("QR status polling rejected due to invalid state")
        yield {"status": "error", "message": "Invalid state"}
        return

    try:
        logger.info("Yielding pending status")
        yield {"status": "pending"}

        def _poll():
            logger.info("Starting wait_for_pass_code...")
            try:
                result = proc.wait_for_pass_code()
                logger.info("QR pass-code polling completed")
                return result
            except exceptions.TimeoutError:
                logger.info("wait_for_pass_code timed out")
                return None

        pass_code = await asyncio.to_thread(_poll)
        if pass_code is None:
            async with session.lock:
                session.state = AuthState.EXPIRED
            logger.info("Yielding expired status")
            yield {"status": "expired"}
            return

        async with session.lock:
            session.state = AuthState.CONFIRMED
            session.last_error = None

        logger.info("Yielding scanned status")
        yield {"status": "scanned"}

        await asyncio.to_thread(proc.complete_auth, pass_code)
        await _activate_authenticated_session(session, "QR")
        logger.info("QR status polling completed")
        yield {"status": "success"}
    except Exception as exc:
        logger.error("QR auth completion failed: %s", type(exc).__name__)
        yield {"status": "error", "message": "Auth completion failed"}
    finally:
        await _release_qr_monitor(session)


async def init_sms_auth(session: Session) -> None:
    def _sync():
        sso_session = HttpxSession(session.client)
        proc = SmsAuthProcedure(**prefabs.BYYT_USTB_EDU_CN, session=sso_session)
        proc.open_auth()
        proc.check_sms_available()
        return proc

    async with session.lock:
        proc = await asyncio.to_thread(_sync)
        session.procedure = proc
        session.state = AuthState.SMS_READY


async def send_sms(session: Session, phone: str) -> None:
    proc: SmsAuthProcedure = session.procedure
    if not proc or session.state not in (AuthState.SMS_READY, AuthState.SMS_SENT):
        raise ValueError("Invalid state for SMS send")

    def _sync():
        proc.send_sms(phone)

    async with session.lock:
        await asyncio.to_thread(_sync)
        session.phone = phone
        session.state = AuthState.SMS_SENT


async def verify_sms(session: Session, phone: str, code: str) -> None:
    proc: SmsAuthProcedure = session.procedure
    if not proc or session.state != AuthState.SMS_SENT:
        raise ValueError("Invalid state for SMS verify")

    def _sync():
        token = proc.submit_sms_code(phone, code)
        try:
            proc.complete_sms_auth(token)
        except exceptions.BadResponseError as exc:
            logger.warning(
                "SMS completion response parse failed; using cookie verification: %s",
                type(exc).__name__,
            )

    await asyncio.to_thread(_sync)
    await _activate_authenticated_session(session, "SMS")
