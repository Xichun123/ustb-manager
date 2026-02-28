from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from app.services import schedule_service
from app.services.session_store import Session
from app.dependencies import get_authenticated_session

router = APIRouter(prefix="/schedule", tags=["schedule"])


class CourseItem(BaseModel):
    key: str = Field(..., description="课程位置标识，如xq1_jc1")
    weekday: int = Field(..., description="星期几，1=周一，7=周日")
    period: int = Field(..., description="节次组，1=1-2节，2=3-4节...")
    start_period: int = Field(..., description="开始节次")
    end_period: int = Field(..., description="结束节次")
    course_name: str = Field(..., description="课程名称")
    course_name_en: str = Field("", description="课程英文名称")
    teacher: str = Field(..., description="授课教师")
    weeks: str = Field(..., description="上课周次")
    location: str = Field(..., description="上课地点")
    period_text: str = Field("", description="节次文本")
    task_code: str = Field("", description="任务号")
    week_bitmap: str = Field("", description="周次位图")


class TermInfo(BaseModel):
    xn: str = Field(..., description="学年，如2025-2026")
    xq: str = Field(..., description="学期，1/2/3")
    xnxq: str = Field(..., description="学年学期，如2025-2026-1")


class WeekItem(BaseModel):
    zc: int = Field(..., description="周次")


class ScheduleResponse(BaseModel):
    schedule: List[dict] = Field(..., description="课程列表")
    dates: dict = Field({}, description="日期映射，键为星期几")
    week: Optional[int] = Field(None, description="当前查询的周次")
    term: str = Field(..., description="学期信息")


@router.get("/current-term", response_model=dict, summary="获取当前学年学期")
async def get_current_term(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    获取当前学年学期信息。

    ## 返回数据
    - XN: 学年，如 "2025-2026"
    - XQ: 学期，如 "1"
    - XNXQ: 学年学期，如 "2025-2026-1"
    """
    return await schedule_service.get_current_term(session)


@router.get("/term-list", response_model=List[dict], summary="获取学期列表")
async def get_term_list(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    获取所有可用的学期列表。

    ## 返回数据
    学期列表，每项包含：
    - dm: 学期代码，如 "2025-2026-1"
    - mc: 学期名称，如 "2025-2026学年第一学期"
    - kssj: 开始时间
    - jssj: 结束时间
    """
    return await schedule_service.get_term_list(session)


@router.get("/week-list", response_model=List[dict], summary="获取周次列表")
async def get_week_list(
    session: Session = Depends(get_authenticated_session),
    xn: Optional[str] = Query(None, description="学年，如2025-2026"),
    xq: Optional[str] = Query(None, description="学期，1/2/3"),
):
    """
    ## 业务说明
    获取指定学期的周次列表。

    ## 返回数据
    周次列表，每项包含 ZC（周次编号）
    """
    return await schedule_service.get_week_list(session, xn, xq)


@router.get("/full", response_model=ScheduleResponse, summary="获取总课表")
async def get_full_schedule(
    session: Session = Depends(get_authenticated_session),
    xn: Optional[str] = Query(None, description="学年，如2025-2026"),
    xq: Optional[str] = Query(None, description="学期，1/2/3"),
):
    """
    ## 业务说明
    获取指定学期的总课表（包含所有周次的课程）。

    ## 使用场景
    - 查看整学期的课程安排
    - 导出课表

    ## 返回数据
    - schedule: 课程列表，包含课程名、教师、地点、时间等
    - term: 学期信息
    """
    if not xn or not xq:
        current = await schedule_service.get_current_term(session)
        xn = xn or current.get("XN", "")
        xq = xq or current.get("XQ", "")

    return await schedule_service.get_schedule_with_dates(session, xn, xq)


@router.get("/week", response_model=ScheduleResponse, summary="获取周课表")
async def get_week_schedule(
    session: Session = Depends(get_authenticated_session),
    xn: Optional[str] = Query(None, description="学年，如2025-2026"),
    xq: Optional[str] = Query(None, description="学期，1/2/3"),
    week: int = Query(..., ge=1, le=99, description="周次，1-99"),
):
    """
    ## 业务说明
    获取指定周的课表。

    ## 使用场景
    - 查看某一周的课程安排
    - 周视图课表展示

    ## 返回数据
    - schedule: 该周的课程列表
    - dates: 该周每天的日期，如 {1: "2025-09-01", 2: "2025-09-02", ...}
    - week: 当前查询的周次
    - term: 学期信息
    """
    if not xn or not xq:
        current = await schedule_service.get_current_term(session)
        xn = xn or current.get("XN", "")
        xq = xq or current.get("XQ", "")

    return await schedule_service.get_schedule_with_dates(session, xn, xq, week)


@router.get("/exams", response_model=List[dict], summary="获取考试安排")
async def get_exam_schedule(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    获取学生的考试安排列表。

    ## 返回数据
    考试列表，每项包含：
    - course_code: 课程代码
    - course_name: 课程名称
    - exam_type: 考试类型（期末/期中）
    - exam_date: 考试日期
    - exam_time: 考试时间
    - weekday: 星期几
    - week_number: 第几周
    - building: 教学楼
    - room: 教室
    - campus: 校区
    """
    return await schedule_service.get_exam_schedule(session)
