import asyncio
import logging
from typing import AsyncGenerator
from ustb_sso import HttpxSession, QrAuthProcedure, SmsAuthProcedure, prefabs, exceptions
from .session_store import Session, AuthState, store

logger = logging.getLogger(__name__)


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
    return qr_bytes


async def start_qr_background_monitor(session: Session):
    """Start QR monitoring in background for polling-based clients (mini program)"""
    proc: QrAuthProcedure = session.procedure
    if not proc or session.state != AuthState.QR_READY:
        return

    # Prevent duplicate monitors
    if getattr(session, '_qr_monitor_started', False):
        return
    session._qr_monitor_started = True

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
                return

            async with session.lock:
                session.state = AuthState.CONFIRMED

            def _complete():
                return proc.complete_auth(pass_code)

            await asyncio.to_thread(_complete)

            def _get_student_id():
                import time as time_module
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = session.client.post("https://byyt.ustb.edu.cn/UserManager/queryxsxx", data="")
                        if resp.status_code == 302 or "session/invalid" in str(resp.url):
                            if attempt < max_retries - 1:
                                time_module.sleep(1)
                                continue
                            raise Exception("Session invalid after auth completion")
                        resp.raise_for_status()
                        data = resp.json()
                        student_id = data.get("content", {}).get("XH") or data.get("XH") or data.get("ID")
                        cookies = {}
                        for cookie in session.client.cookies.jar:
                            if 'ustb.edu.cn' in cookie.domain:
                                cookies[cookie.name] = cookie.value
                        return student_id, cookies
                    except Exception as e:
                        if attempt < max_retries - 1:
                            time_module.sleep(1)
                        else:
                            raise

            student_id, cookies = await asyncio.to_thread(_get_student_id)

            async with session.lock:
                session.state = AuthState.ACTIVE
                session.authenticated = True
                session.student_id = student_id

            if student_id and cookies:
                from . import cookie_store
                cookie_store.save_cookies(student_id, cookies)
                if session.session_id:
                    store.persist(session.session_id, student_id)

            logger.info(f"QR background monitor completed, student_id={student_id}")
        except Exception as e:
            logger.error(f"QR background monitor error: {e}")

    asyncio.create_task(_monitor())


async def poll_qr_status(session: Session) -> AsyncGenerator[dict, None]:
    logger.info(f"poll_qr_status started, state={session.state}")
    proc: QrAuthProcedure = session.procedure
    if not proc or session.state != AuthState.QR_READY:
        logger.error(f"Invalid state: proc={proc}, state={session.state}")
        yield {"status": "error", "message": "Invalid state"}
        return

    logger.info("Yielding pending status")
    yield {"status": "pending"}

    def _poll():
        logger.info("Starting wait_for_pass_code...")
        try:
            result = proc.wait_for_pass_code()
            logger.info(f"wait_for_pass_code returned: {result}")
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

    logger.info("Yielding scanned status")
    yield {"status": "scanned"}

    def _complete():
        logger.info("Completing auth...")
        return proc.complete_auth(pass_code)

    try:
        await asyncio.to_thread(_complete)

        # 获取学生ID和Cookie，带重试逻辑
        def _get_student_id():
            import time as time_module
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = session.client.post("https://byyt.ustb.edu.cn/UserManager/queryxsxx", data="")
                    # 检查是否被重定向到登录页
                    if resp.status_code == 302 or "session/invalid" in str(resp.url):
                        logger.warning(f"Session invalid, attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            time_module.sleep(1)
                            continue
                        raise Exception("Session invalid after auth completion")

                    resp.raise_for_status()
                    data = resp.json()
                    student_id = data.get("content", {}).get("XH") or data.get("XH") or data.get("ID")

                    # 获取cookies
                    cookies = {}
                    for cookie in session.client.cookies.jar:
                        if 'ustb.edu.cn' in cookie.domain:
                            cookies[cookie.name] = cookie.value

                    return student_id, cookies
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        time_module.sleep(1)
                    else:
                        raise

        student_id, cookies = await asyncio.to_thread(_get_student_id)

        async with session.lock:
            session.state = AuthState.ACTIVE
            session.authenticated = True
            session.student_id = student_id

        # 保存Cookie到本地并持久化session
        if student_id and cookies:
            from . import cookie_store
            cookie_store.save_cookies(student_id, cookies)
            # 持久化 session 映射，支持后端重启后恢复
            if session.session_id:
                store.persist(session.session_id, student_id)

        logger.info(f"Yielding success status, student_id={student_id}")
        yield {"status": "success"}
    except Exception as e:
        logger.error(f"Auth completion failed: {e}")
        yield {"status": "error", "message": "Auth completion failed"}


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
        proc.complete_sms_auth(token)

    await asyncio.to_thread(_sync)

    # 获取学生ID和Cookie
    def _get_student_id():
        resp = session.client.post("https://byyt.ustb.edu.cn/UserManager/queryxsxx", data="")
        resp.raise_for_status()
        data = resp.json()
        student_id = data.get("content", {}).get("XH") or data.get("XH") or data.get("ID")
        
        # 获取cookies
        cookies = {}
        for cookie in session.client.cookies.jar:
            if 'ustb.edu.cn' in cookie.domain:
                cookies[cookie.name] = cookie.value
        
        return student_id, cookies

    student_id, cookies = await asyncio.to_thread(_get_student_id)

    async with session.lock:
        session.state = AuthState.ACTIVE
        session.authenticated = True
        session.student_id = student_id

    # 保存Cookie到本地并持久化session
    if student_id and cookies:
        from . import cookie_store
        cookie_store.save_cookies(student_id, cookies)
        # 持久化 session 映射，支持后端重启后恢复
        if session.session_id:
            store.persist(session.session_id, student_id)