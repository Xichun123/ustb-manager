from fastapi import APIRouter, Cookie, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from app.services import grades_service
from app.services.session_store import store
from app.exceptions import BYYTSessionExpired
import logging

router = APIRouter(prefix="/grades", tags=["grades"])
logger = logging.getLogger(__name__)


# Response Models
class GPAStats(BaseModel):
    gpa: float = Field(..., description="GPA")
    total_credits: float = Field(..., description="总学分")
    passed_credits: float = Field(..., description="已通过学分")
    failed_count: int = Field(..., description="不及格门数")

    class Config:
        json_schema_extra = {
            "example": {
                "gpa": 3.75,
                "total_credits": 120.5,
                "passed_credits": 118.0,
                "failed_count": 1
            }
        }


class GradeItem(BaseModel):
    course_name: str = Field(..., description="课程名称")
    course_code: str = Field(..., description="课程代码")
    credit: float = Field(..., description="学分")
    score: str = Field(..., description="成绩")
    gpa: Optional[float] = Field(None, description="绩点")
    
    class Config:
        json_schema_extra = {
            "example": {
                "course_name": "高等数学A(1)",
                "course_code": "MATH101",
                "credit": 5.0,
                "score": "92",
                "gpa": 4.0
            }
        }


class GradesListResponse(BaseModel):
    grades: List[dict] = Field(..., description="成绩列表")
    total: int = Field(..., description="总记录数")
    gpa_stats: GPAStats = Field(..., description="GPA统计信息")


class StudentInfoResponse(BaseModel):
    student_id: str = Field(..., description="学号")
    name: str = Field(..., description="姓名")
    major: Optional[str] = Field(None, description="专业")
    class_name: Optional[str] = Field(None, description="班级")
    
    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "41234567",
                "name": "张三",
                "major": "计算机科学与技术",
                "class_name": "计算机2021-1班"
            }
        }


@router.get("/list", response_model=GradesListResponse, summary="获取成绩列表")
async def get_grades(
    ustb_sid: Optional[str] = Cookie(None),
    page_num: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(100, ge=1, le=200, description="每页记录数，最大200"),
    xn: Optional[str] = Query(None, description="学年，格式：2023-2024"),
    xq: Optional[str] = Query(None, description="学期，1=第一学期，2=第二学期，3=夏季学期"),
    kcxz: Optional[str] = Query(None, description="课程性质，如：必修、选修"),
    kclb: Optional[str] = Query(None, description="课程类别"),
):
    """
    ## 业务说明
    获取学生的成绩列表，支持分页和多维度筛选。同时计算GPA统计信息。
    
    ## 使用场景
    - 成绩查询页面展示成绩列表
    - 按学年学期筛选成绩
    - 按课程性质（必修/选修）筛选
    - 查看GPA统计
    
    ## 筛选参数说明
    - `xn`: 学年，如 "2023-2024"
    - `xq`: 学期代码
      - 1: 第一学期（秋季）
      - 2: 第二学期（春季）
      - 3: 夏季学期
    - `kcxz`: 课程性质，常见值：
      - "必修": 必修课
      - "选修": 选修课
      - "任选": 任意选修
    - `kclb`: 课程类别，如 "通识教育课"、"专业课" 等
    
    ## 返回数据
    - `grades`: 成绩列表，包含课程名称、学分、成绩、绩点等
    - `total`: 符合条件的总记录数
    - `gpa_stats`: GPA统计
      - `total_gpa`: 算术平均GPA
      - `weighted_gpa`: 学分加权GPA
      - `total_credits`: 总学分
    
    ## 注意事项
    - 需要先登录认证
    - 分页参数：page_num从1开始，page_size最大200
    - 不传筛选参数时返回所有成绩
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_grades(
            session=session,
            page_num=page_num,
            page_size=page_size,
            xn=xn,
            xq=xq,
            kcxz=kcxz,
            kclb=kclb,
        )

        # 计算GPA
        grades_list = result.get("list", [])
        gpa_stats = grades_service.calculate_gpa(grades_list)

        return {
            "grades": grades_list,
            "total": result.get("total", 0),
            "gpa_stats": gpa_stats,
        }

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch grades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student-info", response_model=dict, summary="获取学生基本信息")
async def get_student_info(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取当前登录学生的基本信息，包括学号、姓名、专业、班级等。
    
    ## 使用场景
    - 个人信息页面展示
    - 页面头部显示用户信息
    - 验证用户身份
    
    ## 返回数据
    返回学生的基本信息字段，具体字段取决于教务系统返回的数据。
    常见字段包括：
    - XH: 学号
    - XM: 姓名
    - ZYMC: 专业名称
    - BJMC: 班级名称
    
    ## 注意事项
    - 需要先登录认证
    - 数据来源于教务系统，字段名为拼音缩写
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_student_info(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch student info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-info", response_model=dict, summary="获取用户完整信息")
async def get_user_info(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取当前用户的完整信息，包含角色、权限等扩展信息。
    
    ## 使用场景
    - 需要完整用户信息的场景
    - 权限验证
    - 用户配置页面
    
    ## 与 student-info 的区别
    - `student-info`: 仅返回学生基本信息
    - `user-info`: 返回完整的用户信息，包括系统角色、权限等
    
    ## 注意事项
    - 需要先登录认证
    - 返回的数据结构可能比 student-info 更复杂
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_user_info(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch user info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student-plan", response_model=list, summary="获取学生培养方案")
async def get_student_plan(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取学生的培养方案信息，包括专业要求、课程计划等。
    
    ## 使用场景
    - 学业规划页面
    - 查看专业培养方案
    - 了解毕业要求
    
    ## 返回数据
    培养方案的详细信息，通常包括：
    - 专业培养目标
    - 课程体系结构
    - 学分要求
    - 必修课程列表
    - 选修课程要求
    
    ## 注意事项
    - 需要先登录认证
    - 数据来源于教务系统
    - 不同专业的培养方案结构可能不同
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_student_plan(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch student plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available-terms", response_model=dict, summary="查询可选学年学期")
async def get_available_terms(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取系统中可用的学年学期列表，用于成绩查询的筛选条件。
    
    ## 使用场景
    - 成绩查询页面的学期选择下拉框
    - 动态获取可查询的学期范围
    
    ## 返回数据
    可用的学年学期列表，通常包括：
    - 学年（如 "2023-2024"）
    - 学期代码（1/2/3）
    - 学期名称（如 "2023-2024学年第一学期"）
    
    ## 注意事项
    - 需要先登录认证
    - 返回的学期列表是动态的，会随着时间更新
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_available_terms(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch available terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/required-course-status", response_model=dict, summary="查询必修课完成情况")
async def get_required_course_status(
    ustb_sid: Optional[str] = Cookie(None),
    jzxnxq: Optional[str] = Query(None, description="截止学年学期，格式：2023-2024-1"),
):
    """
    ## 业务说明
    查询学生必修课程的完成情况，用于了解学业进度。
    
    ## 使用场景
    - 学业进度页面
    - 毕业审核
    - 了解必修课完成度
    
    ## 参数说明
    - `jzxnxq`: 截止学年学期，格式为 "学年-学期"
      - 例如: "2023-2024-1" 表示2023-2024学年第一学期
      - 不传则查询所有学期
    
    ## 返回数据
    必修课完成情况统计，通常包括：
    - 应修必修课列表
    - 已完成的必修课
    - 未完成的必修课
    - 完成率统计
    
    ## 注意事项
    - 需要先登录认证
    - 数据基于培养方案和已修课程计算
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_required_course_status(session, jzxnxq)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch required course status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/term-list", response_model=dict, summary="查询学年学期列表")
async def get_term_list(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取完整的学年学期列表，包含更详细的学期信息。
    
    ## 使用场景
    - 学期选择器
    - 学期信息展示
    - 学期相关的数据查询
    
    ## 与 available-terms 的区别
    - `available-terms`: 返回可用于成绩查询的学期
    - `term-list`: 返回更完整的学期列表和详细信息
    
    ## 返回数据
    学期列表，每个学期包含：
    - 学年学期代码
    - 学期名称
    - 开始结束时间
    - 当前状态等
    
    ## 注意事项
    - 需要先登录认证
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_term_list(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch term list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credit-completion-status", response_model=dict, summary="获取学分完成情况")
async def get_credit_completion_status(ustb_sid: Optional[str] = Cookie(None)):
    """
    ## 业务说明
    获取学生的学分完成情况统计，包括各类课程的学分完成度。
    
    ## 使用场景
    - 学业进度仪表盘
    - 毕业资格审核
    - 学分统计分析
    
    ## 返回数据
    学分完成情况统计，通常包括：
    - 总学分要求
    - 已获得学分
    - 各类课程学分统计：
      - 必修课学分
      - 选修课学分
      - 通识教育课学分
      - 专业课学分
    - 完成百分比
    
    ## 注意事项
    - 需要先登录认证
    - 数据来源于教务系统
    - 统计基于培养方案和已修课程
    """
    if not ustb_sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = store.get(ustb_sid)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if not session.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = await grades_service.get_credit_completion_status(session)
        return result

    except BYYTSessionExpired as e:
        logger.warning(f"BYYT session expired: {e}")
        # 返回 502 而不是 401，因为这是 BYYT 系统的问题，不是本地认证问题
        raise HTTPException(status_code=502, detail="BYYT session expired, please login again")
    except Exception as e:
        logger.error(f"Failed to fetch credit completion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))