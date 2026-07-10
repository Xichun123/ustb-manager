from fastapi import APIRouter, Depends, Query

from app.byyt.notices import query_notices
from app.dependencies import get_authenticated_session
from app.models.notices import NoticePage
from app.services.session_store import Session

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("", response_model=NoticePage, summary="查询通知公告")
async def notices(
    session: Session = Depends(get_authenticated_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await query_notices(session, page=page, page_size=page_size)
