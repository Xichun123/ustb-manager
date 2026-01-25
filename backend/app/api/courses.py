"""选课管理 API 路由"""
from fastapi import APIRouter, Cookie, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from app.services import course_service
from app.services.session_store import store
from app.exceptions import BYYTSessionExpired
import logging

router = APIRouter(prefix="/courses", tags=["courses"])
logger = logging.getLogger(__name__)


class CourseItem(BaseModel):
    task_id: str = Field(..., description="任务号（唯一标识）")
    course_code: str = Field(..., description="课程代码")
    course_name: str = Field(..., description="课程名称")
    course_name_en: str = Field("", description="课程英文名称")
    course_type: str = Field(..., description="课程性质（必修/任选）")
    category: str = Field(..., description="课程类别")
    credits: str = Field(..., description="学分")
    hours: str = Field(..., description="学时")
    selection_method: str = Field(..., description="选课方式")
    college: str = Field(..., description="开课学院")
    campus: str = Field(..., description="校区")
    teacher: str = Field(..., description="教师")
    capacity: str = Field("", description="总容量")
    selected_count: str = Field("", description="已选人数")
    selection_time: str = Field("", description="选课时间")
    withdraw_start: str = Field("", description="可退选开始时间")
    withdraw_end: str = Field("", description="可退选结束时间")


class SelectedCoursesResponse(BaseModel):
    courses: List[dict] = Field(..., description="已选课程列表")
    total: int = Field(..., description="课程总数")
    total_credits: float = Field(..., description="总学分")


class TermInfoResponse(BaseModel):
    p_xn: str = Field(..., description="选课学年")
    p_xq: str = Field(..., description="选课学期")
    p_xnxq: str = Field(..., description="选课学年学期")
    p_dqxn: str = Field(..., description="当前学年")
    p_dqxq: str = Field(..., description="当前学期")
    p_dqxnxq: str = Field(..., description="当前学年学期")


class TermListItem(BaseModel):
    dm: str = Field(..., description="学期代码")
    mc: str = Field(..., description="学期名称")


class CollegeItem(BaseModel):
    code: str = Field(..., description="学院代码")
    name: str = Field(..., description="学院名称")


class CategoryItem(BaseModel):
    code: str = Field(..., description="类别代码")
    name: str = Field(..., description="类别名称")


class CampusItem(BaseModel):
    code: str = Field(..., description="校区代码")
    name: str = Field(..., description="校区名称")


def _get_session(ustb_sid: Optional[str]):
    """获取并验证会话"""
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return session


@router.get("/term-info", response_model=dict, summary="获取选课学期信息")
async def get_term_info(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取选课系统当前学年学期信息，包括当前学期和选课学期。

    ## 返回数据
    - p_xn: 选课学年
    - p_xq: 选课学期
    - p_xnxq: 选课学年学期
    - p_dqxn: 当前学年
    - p_dqxq: 当前学期
    - p_dqxnxq: 当前学年学期
    """
    session = _get_session(ustb_sid)

    try:
        result = await course_service.get_course_term_info(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch course term info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/term-list", response_model=List[TermListItem], summary="获取开课学期列表")
async def get_term_list(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取可供选课的学期列表。

    ## 返回数据
    学期列表，每项包含：
    - dm: 学期代码（如 2025-20262）
    - mc: 学期名称（如 2025-2026-2）
    """
    session = _get_session(ustb_sid)

    try:
        result = await course_service.get_course_term_list(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch course term list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selected", response_model=SelectedCoursesResponse, summary="获取已选课程列表")
async def get_selected_courses(
    ustb_sid: Optional[str] = Cookie(None),
    xn: Optional[str] = Query(None, description="选课学年，如 2025-2026"),
    xq: Optional[str] = Query(None, description="选课学期，如 2"),
):
    """
    ## 业务说明
    获取学生已选课程的详细列表。

    ## 参数说明
    - xn: 选课学年（可选，不传则使用当前选课学年）
    - xq: 选课学期（可选，不传则使用当前选课学期）

    ## 返回数据
    - courses: 已选课程列表
    - total: 课程总数
    - total_credits: 总学分
    """
    session = _get_session(ustb_sid)

    try:
        # 先获取学期信息
        term_info = await course_service.get_course_term_info(session)

        # 使用传入的学期或默认使用选课学期
        use_xn = xn or term_info.get("p_xn", "")
        use_xq = xq or term_info.get("p_xq", "")
        use_xnxq = f"{use_xn}{use_xq}" if use_xn and use_xq else term_info.get("p_xnxq", "")

        result = await course_service.get_selected_courses(
            session,
            xn=use_xn,
            xq=use_xq,
            xnxq=use_xnxq,
            dqxn=term_info.get("p_dqxn", ""),
            dqxq=term_info.get("p_dqxq", ""),
            dqxnxq=term_info.get("p_dqxnxq", ""),
        )
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch selected courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available", response_model=dict, summary="获取可选课程列表")
async def get_available_courses(
    ustb_sid: Optional[str] = Cookie(None),
    xn: Optional[str] = Query(None, description="选课学年，如 2025-2026"),
    xq: Optional[str] = Query(None, description="选课学期，如 2"),
    method: str = Query("bx-b-b", description="选课方式: bx-b-b(必修), mooc-b-b(MOOC), sztzk(素质拓展), zytzk(专业拓展), ggkrw(公共课)"),
    college: Optional[str] = Query(None, description="开课学院代码"),
    category: Optional[str] = Query(None, description="课程类别代码"),
    campus: Optional[str] = Query(None, description="校区代码"),
    keyword: Optional[str] = Query(None, description="课程关键字搜索"),
):
    """
    ## 业务说明
    获取可选课程列表，支持按选课方式、学院、类别、校区筛选。

    ## 参数说明
    - method: 选课方式代码
      - `bx-b-b`: 必修课
      - `mooc-b-b`: MOOC在线课程
      - `sztzk`: 素质拓展课
      - `zytzk`: 专业拓展课
      - `ggkrw`: 公共课
    - college: 开课学院代码（通过 /courses/colleges 获取）
    - category: 课程类别代码（通过 /courses/categories 获取）
    - campus: 校区代码（通过 /courses/campuses 获取）
    - keyword: 课程名称关键字

    ## 返回数据
    - courses: 可选课程列表
    - total: 课程总数
    - total_credits: 总学分
    - selection_method: 当前查询的选课方式
    """
    session = _get_session(ustb_sid)

    try:
        # 先获取学期信息
        term_info = await course_service.get_course_term_info(session)

        # 使用传入的学期或默认使用选课学期
        use_xn = xn or term_info.get("p_xn", "")
        use_xq = xq or term_info.get("p_xq", "")
        use_xnxq = f"{use_xn}{use_xq}" if use_xn and use_xq else term_info.get("p_xnxq", "")

        result = await course_service.get_available_courses(
            session,
            xn=use_xn,
            xq=use_xq,
            xnxq=use_xnxq,
            dqxn=term_info.get("p_dqxn", ""),
            dqxq=term_info.get("p_dqxq", ""),
            dqxnxq=term_info.get("p_dqxnxq", ""),
            xkfsdm=method,
            kkyx=college or "",
            kclb=category or "",
            xiaoqu=campus or "",
            gjz=keyword or "",
        )
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch available courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/colleges", response_model=List[CollegeItem], summary="获取开课学院列表")
async def get_colleges(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取所有开课学院的列表，用于筛选课程。

    ## 返回数据
    学院列表，每项包含：
    - code: 学院代码
    - name: 学院名称
    """
    session = _get_session(ustb_sid)

    try:
        result = await course_service.get_colleges(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch colleges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=List[CategoryItem], summary="获取课程类别列表")
async def get_categories(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取所有课程类别的列表，用于筛选课程。

    ## 返回数据
    类别列表，每项包含：
    - code: 类别代码
    - name: 类别名称
    """
    session = _get_session(ustb_sid)

    try:
        result = await course_service.get_course_categories(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campuses", response_model=List[CampusItem], summary="获取校区列表")
async def get_campuses(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取所有校区的列表，用于筛选课程。

    ## 返回数据
    校区列表，每项包含：
    - code: 校区代码
    - name: 校区名称
    """
    session = _get_session(ustb_sid)

    try:
        result = await course_service.get_campuses(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch campuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))
