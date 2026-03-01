"""选课管理 API 路由"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from app.services import course_service
from app.services.session_store import Session
from app.dependencies import get_authenticated_session

router = APIRouter(prefix="/courses", tags=["courses"])


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


class CourseOperationRequest(BaseModel):
    course_id: str = Field(..., description="课程任务 ID")
    method: str = Field("bx-b-b", description="选课方式代码")


class CartRemoveRequest(BaseModel):
    course_ids: List[str] = Field(..., description="要移除的课程 ID 列表")
    method: str = Field("bx-b-b", description="选课方式代码")


class CourseOperationResponse(BaseModel):
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")


@router.get("/term-info", response_model=dict, summary="获取选课学期信息")
async def get_term_info(session: Session = Depends(get_authenticated_session)):
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
    return await course_service.get_course_term_info(session)


@router.get("/term-list", response_model=List[TermListItem], summary="获取开课学期列表")
async def get_term_list(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    获取可供选课的学期列表。

    ## 返回数据
    学期列表，每项包含：
    - dm: 学期代码（如 2025-20262）
    - mc: 学期名称（如 2025-2026-2）
    """
    return await course_service.get_course_term_list(session)


@router.get("/selected", response_model=SelectedCoursesResponse, summary="获取已选课程列表")
async def get_selected_courses(
    session: Session = Depends(get_authenticated_session),
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
    tp = await _get_term_params(session, xn, xq)
    return await course_service.get_selected_courses(
        session,
        xn=tp["xn"],
        xq=tp["xq"],
        xnxq=tp["xnxq"],
        dqxn=tp["dqxn"],
        dqxq=tp["dqxq"],
        dqxnxq=tp["dqxnxq"],
    )


@router.get("/available", response_model=dict, summary="获取可选课程列表")
async def get_available_courses(
    session: Session = Depends(get_authenticated_session),
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
    tp = await _get_term_params(session, xn, xq)
    return await course_service.get_available_courses(
        session,
        xn=tp["xn"],
        xq=tp["xq"],
        xnxq=tp["xnxq"],
        dqxn=tp["dqxn"],
        dqxq=tp["dqxq"],
        dqxnxq=tp["dqxnxq"],
        xkfsdm=method,
        kkyx=college or "",
        kclb=category or "",
        xiaoqu=campus or "",
        gjz=keyword or "",
    )


@router.get("/colleges", response_model=List[CollegeItem], summary="获取开课学院列表")
async def get_colleges(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    获取所有开课学院的列表，用于筛选课程。

    ## 返回数据
    学院列表，每项包含：
    - code: 学院代码
    - name: 学院名称
    """
    return await course_service.get_colleges(session)


@router.get("/categories", response_model=List[CategoryItem], summary="获取课程类别列表")
async def get_categories(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    获取所有课程类别的列表，用于筛选课程。

    ## 返回数据
    类别列表，每项包含：
    - code: 类别代码
    - name: 类别名称
    """
    return await course_service.get_course_categories(session)


@router.get("/campuses", response_model=List[CampusItem], summary="获取校区列表")
async def get_campuses(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    获取所有校区的列表，用于筛选课程。

    ## 返回数据
    校区列表，每项包含：
    - code: 校区代码
    - name: 校区名称
    """
    return await course_service.get_campuses(session)


# ==================== 辅助函数 ====================

async def _get_term_params(session: Session, xn: Optional[str] = None, xq: Optional[str] = None):
    """获取学期参数，未指定时自动使用当前学期"""
    term_info = await course_service.get_course_term_info(session)
    use_xn = xn or term_info.get("p_xn", "")
    use_xq = xq or term_info.get("p_xq", "")
    use_xnxq = f"{use_xn}{use_xq}" if use_xn and use_xq else term_info.get("p_xnxq", "")
    return {
        "xn": use_xn,
        "xq": use_xq,
        "xnxq": use_xnxq,
        "dqxn": term_info.get("p_dqxn", ""),
        "dqxq": term_info.get("p_dqxq", ""),
        "dqxnxq": term_info.get("p_dqxnxq", ""),
    }


# ==================== 选课操作 ====================


@router.post("/select", response_model=CourseOperationResponse, summary="选课")
async def select_course(
    req: CourseOperationRequest,
    session: Session = Depends(get_authenticated_session),
):
    """
    ## 业务说明
    直接选择一门课程（先到先得模式）。

    ## 参数说明
    - `course_id`: 课程任务 ID，可通过 `/courses/available` 获取可选课程列表中的 `id` 字段
    - `method`: 选课方式代码（默认 bx-b-b 必修）

    ## 选课方式代码
    - `bx-b-b`: 必修课
    - `mooc-b-b`: MOOC
    - `sztzk`: 素质拓展课
    - `zytzk`: 专业拓展课
    - `ggkrw`: 公共课

    ## 返回数据
    - `success`: 是否成功
    - `message`: 操作结果描述
    """
    tp = await _get_term_params(session)
    return await course_service.select_course(
        session, req.course_id, **tp, xkfsdm=req.method,
    )


@router.post("/drop", response_model=CourseOperationResponse, summary="退课")
async def drop_course(
    req: CourseOperationRequest,
    session: Session = Depends(get_authenticated_session),
):
    """
    ## 业务说明
    退选一门已选课程。

    ## 参数说明
    - `course_id`: 已选课程的 ID，可通过 `/courses/selected` 获取
    - `method`: 选课方式代码

    ## 注意事项
    - 退课有时间限制，超过退课截止时间将无法退课
    - 必修课退课需谨慎
    """
    tp = await _get_term_params(session)
    return await course_service.drop_course(
        session, req.course_id, **tp, xkfsdm=req.method,
    )


# ==================== 购物车操作 ====================


@router.get("/cart", response_model=SelectedCoursesResponse, summary="查询选课购物车")
async def get_cart(
    session: Session = Depends(get_authenticated_session),
    method: str = Query("bx-b-b", description="选课方式代码"),
):
    """
    ## 业务说明
    查询当前购物车中的课程列表。

    ## 返回数据
    - `courses`: 购物车中的课程列表
    - `total`: 课程总数
    - `total_credits`: 总学分
    """
    tp = await _get_term_params(session)
    return await course_service.get_cart(session, **tp, xkfsdm=method)


@router.post("/cart/add", response_model=CourseOperationResponse, summary="添加课程到购物车")
async def add_to_cart(
    req: CourseOperationRequest,
    session: Session = Depends(get_authenticated_session),
):
    """
    ## 业务说明
    将一门可选课程添加到购物车（不直接选课）。

    ## 使用场景
    - 意愿选课模式下先加入购物车
    - 需要比较多门课程后再确认选课
    """
    tp = await _get_term_params(session)
    return await course_service.add_to_cart(
        session, req.course_id, **tp, xkfsdm=req.method,
    )


@router.post("/cart/remove", response_model=CourseOperationResponse, summary="从购物车移除课程")
async def remove_from_cart(
    req: CartRemoveRequest,
    session: Session = Depends(get_authenticated_session),
):
    """
    ## 业务说明
    从购物车中移除一门或多门课程。

    ## 参数说明
    - `course_ids`: 要移除的课程 ID 列表（支持批量操作）
    """
    tp = await _get_term_params(session)
    return await course_service.remove_from_cart(
        session, req.course_ids, **tp, xkfsdm=req.method,
    )


@router.post("/cart/submit", response_model=CourseOperationResponse, summary="提交购物车确认选课")
async def submit_cart(
    session: Session = Depends(get_authenticated_session),
    method: str = Query("bx-b-b", description="选课方式代码"),
):
    """
    ## 业务说明
    将购物车中的所有课程提交确认选课。

    ## 注意事项
    - 购物车中的所有课程将被批量提交
    - 提交后无法撤回，需要通过退课操作
    """
    tp = await _get_term_params(session)
    return await course_service.submit_cart(session, **tp, xkfsdm=method)


# ==================== 选课日志 ====================


@router.get("/selection-log", response_model=list, summary="查询选课操作日志")
async def get_selection_log(
    session: Session = Depends(get_authenticated_session),
):
    """
    ## 业务说明
    查询本学期的选课操作日志。

    ## 返回数据
    选课操作记录列表，包含选课/退课的操作时间和详情。
    """
    tp = await _get_term_params(session)
    return await course_service.get_selection_log(session, **tp)
