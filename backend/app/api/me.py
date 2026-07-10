from fastapi import APIRouter, Depends

from app.byyt.profile import get_user_profile
from app.dependencies import get_authenticated_session
from app.models.profile import UserProfile
from app.services.session_store import Session

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserProfile, summary="获取当前学生信息")
async def me(session: Session = Depends(get_authenticated_session)):
    return await get_user_profile(session)
