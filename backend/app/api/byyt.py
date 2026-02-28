from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from pydantic import BaseModel, Field

from ..services.session_store import Session, AuthState
from ..services import byyt_proxy
from ..dependencies import get_authenticated_session

router = APIRouter(prefix="/byyt", tags=["byyt"])


@router.get("/grades", response_model=dict, summary="获取BYYT系统成绩")
async def grades(
    session: Session = Depends(get_authenticated_session),
    semester: Optional[str] = Query(None, description="学期代码，不传则返回所有学期成绩"),
):
    """
    ## 业务说明
    从BYYT（北科大教务）系统获取学生成绩数据。这是一个底层API，直接访问BYYT系统。

    ## 使用场景
    - 需要获取原始BYYT系统数据
    - 与 `/grades/list` 相比，这是更底层的接口
    - 适合需要BYYT系统原始数据格式的场景

    ## 参数说明
    - `semester`: 学期代码（可选）
      - 不传则返回所有学期的成绩
      - 传入特定学期代码则只返回该学期成绩

    ## 返回数据
    返回BYYT系统的原始成绩数据，数据结构由BYYT系统定义。

    ## 与 /grades/list 的区别
    - `/api/grades/list`: 经过处理的成绩数据，包含GPA计算、分页等功能
    - `/api/byyt/grades`: BYYT系统的原始数据，未经处理

    ## 注意事项
    - 需要先登录认证
    - 返回的数据格式为BYYT系统原始格式
    - 如果BYYT系统不可用，会返回502错误
    """
    try:
        return await byyt_proxy.get_grades(session, semester)
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/profile", response_model=dict, summary="获取BYYT系统用户信息")
async def profile(session: Session = Depends(get_authenticated_session)):
    """
    ## 业务说明
    从BYYT系统获取用户的个人信息和档案数据。

    ## 使用场景
    - 获取用户在BYYT系统中的完整档案
    - 需要BYYT系统原始用户数据
    - 用户信息展示

    ## 返回数据
    返回BYYT系统的用户档案数据，通常包括：
    - 基本信息（姓名、学号、性别等）
    - 学籍信息（专业、班级、入学年份等）
    - 联系方式
    - 其他档案信息

    ## 与 /grades/student-info 的区别
    - `/api/grades/student-info`: 简化的学生基本信息
    - `/api/byyt/profile`: BYYT系统的完整用户档案

    ## 注意事项
    - 需要先登录认证
    - 返回的数据格式为BYYT系统原始格式
    - 如果BYYT系统不可用，会返回502错误
    - 数据字段名通常为拼音缩写
    """
    try:
        return await byyt_proxy.get_profile(session)
    except Exception as e:
        raise HTTPException(502, str(e))
