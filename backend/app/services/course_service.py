"""选课管理服务"""
import asyncio
import logging
from typing import Dict, List, Optional
from app.services.session_store import Session
from app.exceptions import BYYTSessionExpired
from app.services.grades_service import _check_byyt_response
from app.services.schedule_service import get_term_list as _get_schedule_term_list
from app.cache import reference_data_cache

logger = logging.getLogger(__name__)


async def get_course_term_info(session: Session) -> Dict:
    """获取选课系统当前学年学期信息"""

    def _fetch():
        # 构造请求参数
        params = (
            "cxsfmt=0&p_pylx=1&mxpylx=1&p_sfgldjr=0&p_sfredis=0&p_sfsyxkgwc=0"
            "&p_xktjz=&p_chaxunxh=&p_gjz=&p_skjs=&p_xn=&p_xq=&p_xnxq="
            "&p_dqxn=&p_dqxq=&p_dqxnxq=&p_xkfsdm=&p_xiaoqu=&p_kkyx=&p_kclb="
            "&p_xkxs=&p_dyc=&p_kkxnxq=&p_id=&p_sfhlctkc=0&p_sfhllrlkc=0"
            "&p_kxsj_xqj=&p_kxsj_ksjc=&p_kxsj_jsjc=&p_kcdm_js=&p_kcdm_cxrw="
            "&p_kcdm_cxrw_zckc=&p_kc_gjz=&p_xzcxtjz_nj=&p_xzcxtjz_yx="
            "&p_xzcxtjz_zy=&p_xzcxtjz_zyfx=&p_xzcxtjz_bj=&p_sfxsgwckb=1"
            "&p_skyy=&p_sfmxzj=0"
        )
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/Xsxk/queryXkdqXnxq",
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)
    return result


async def get_course_term_list(session: Session) -> List[Dict]:
    """获取开课学期列表 - 复用课表服务的学期列表"""
    return await _get_schedule_term_list(session)


async def get_selected_courses(
    session: Session,
    xn: str,
    xq: str,
    xnxq: str,
    dqxn: str,
    dqxq: str,
    dqxnxq: str,
) -> Dict:
    """获取已选课程列表

    Args:
        session: 用户会话
        xn: 选课学年（如 2025-2026）
        xq: 选课学期（如 2）
        xnxq: 选课学年学期（如 2025-20262）
        dqxn: 当前学年
        dqxq: 当前学期
        dqxnxq: 当前学年学期
    """

    def _fetch():
        params = {
            "cxsfmt": "1",
            "p_pylx": "1",
            "mxpylx": "1",
            "p_sfgldjr": "0",
            "p_sfredis": "0",
            "p_sfsyxkgwc": "0",
            "p_xktjz": "",
            "p_chaxunxh": "",
            "p_gjz": "",
            "p_skjs": "",
            "p_xn": xn,
            "p_xq": xq,
            "p_xnxq": xnxq,
            "p_dqxn": dqxn,
            "p_dqxq": dqxq,
            "p_dqxnxq": dqxnxq,
            "p_xkfsdm": "yixuan",  # 已选
            "p_xiaoqu": "",
            "p_kkyx": "",
            "p_kclb": "",
            "p_xkxs": "",
            "p_dyc": "",
            "p_kkxnxq": "",
            "p_id": "",
            "p_sfhlctkc": "0",
            "p_sfhllrlkc": "0",
            "p_kxsj_xqj": "",
            "p_kxsj_ksjc": "",
            "p_kxsj_jsjc": "",
            "p_kcdm_js": "",
            "p_kcdm_cxrw": "",
            "p_kcdm_cxrw_zckc": "",
            "p_kc_gjz": "",
            "p_xzcxtjz_nj": "",
            "p_xzcxtjz_yx": "",
            "p_xzcxtjz_zy": "",
            "p_xzcxtjz_zyfx": "",
            "p_xzcxtjz_bj": "",
            "p_sfxsgwckb": "1",
            "p_skyy": "",
            "p_sfmxzj": "",
            "p_chaxunxkfsdm": "",
        }
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/Xsxk/queryYxkc",
            data=params,
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)

    # 解析返回数据
    courses = []
    if isinstance(result, dict):
        raw_courses = result.get("yxkcList", [])
        for course in raw_courses:
            courses.append(_parse_course(course))

    return {
        "courses": courses,
        "total": len(courses),
        "total_credits": sum(float(c.get("credits", 0)) for c in courses),
    }


def _parse_available_course(course: Dict) -> Dict:
    """解析可选课程数据（来自 kxrwList）"""
    # xkzt 表示选课状态: "未选" 或 "已选"
    is_selected = course.get("xkzt", "") == "已选"

    return {
        "task_id": course.get("rwh", "") or course.get("id", ""),  # 任务号
        "course_code": course.get("kcdm", ""),  # 课程代码
        "course_name": course.get("kcmc", ""),  # 课程名称
        "course_name_en": course.get("kcmc_en", ""),  # 英文名称
        "course_type": course.get("kcxzmc", ""),  # 课程性质（必修/任选）
        "course_type_code": course.get("kcxz", ""),  # 课程性质代码
        "category": course.get("kclbmc", ""),  # 课程类别
        "category_code": course.get("kclb", ""),  # 课程类别代码
        "credits": course.get("xf", "0"),  # 学分
        "hours": course.get("zxs", "") or course.get("xszxs", "0"),  # 学时（总学时或学生学时）
        "selection_method": course.get("rwlxmc", ""),  # 选课方式
        "selection_method_code": course.get("xkfsdm", ""),  # 选课方式代码
        "college": course.get("kkyxmc", ""),  # 开课学院
        "college_code": course.get("kkyx", ""),  # 开课学院代码
        "campus": course.get("xiaoqumc", ""),  # 校区
        "campus_code": course.get("xiaoqu", ""),  # 校区代码
        "capacity": course.get("zrl", ""),  # 总容量
        "selected_count": course.get("yxzrs", ""),  # 已选人数
        "teacher": course.get("dgjsmc", ""),  # 教师
        "task_name": course.get("rwmc", ""),  # 任务名称
        "schedule_time": course.get("sksj", ""),  # 上课时间
        "schedule_location": course.get("skdd", ""),  # 上课地点
        "schedule_html": course.get("pkjgmx", ""),  # 排课结果明细（HTML）
        "selection_time": "",  # 可选课程无选课时间
        "withdraw_start": "",  # 可选课程无退选时间
        "withdraw_end": "",
        "selection_status": course.get("xkzt", ""),  # 选课状态（未选/已选）
        "lottery_status": "",  # 抽签状态
        "needs_payment": False,
        "needs_approval": False,
        "course_info": course.get("kcxx", ""),  # 课程信息（HTML）
        "class_number": course.get("kxh", ""),  # 课序号
        "is_selected": is_selected,  # 是否已选
    }


def _parse_course(course: Dict) -> Dict:
    """解析单个课程数据（已选课程列表）"""
    return {
        "task_id": course.get("rwh", ""),  # 任务号（唯一标识）
        "course_code": course.get("kcdm", ""),  # 课程代码
        "course_name": course.get("kcmc", ""),  # 课程名称
        "course_name_en": course.get("kcmc_en", ""),  # 英文名称
        "course_type": course.get("kcxzmc", ""),  # 课程性质（必修/任选）
        "course_type_code": course.get("kcxz", ""),  # 课程性质代码
        "category": course.get("kclbmc", ""),  # 课程类别
        "category_code": course.get("kclb", ""),  # 课程类别代码
        "credits": course.get("xf", "0"),  # 学分
        "hours": course.get("xs", "0"),  # 学时
        "selection_method": course.get("xkfsmc", ""),  # 选课方式
        "selection_method_code": course.get("xkfsdm", ""),  # 选课方式代码
        "college": course.get("kkyxmc", ""),  # 开课学院
        "college_code": course.get("kkyx", ""),  # 开课学院代码
        "campus": course.get("xiaoqumc", ""),  # 校区
        "campus_code": course.get("xiaoqu", ""),  # 校区代码
        "capacity": course.get("zrl", ""),  # 总容量
        "selected_count": course.get("yxzrs", ""),  # 已选人数
        "teacher": course.get("dgjsmc", ""),  # 教师
        "task_name": course.get("rwmc", ""),  # 任务名称
        "schedule_time": course.get("sksj", ""),  # 上课时间
        "schedule_location": course.get("skdd", ""),  # 上课地点
        "schedule_html": course.get("pkjgmx", ""),  # 排课结果明细（HTML）
        "selection_time": course.get("xksj", ""),  # 选课时间
        "withdraw_start": course.get("ktxkkssj", ""),  # 可退选开始时间
        "withdraw_end": course.get("ktxkjssj", ""),  # 可退选结束时间
        "selection_status": course.get("xkbj", ""),  # 选课标记
        "lottery_status": course.get("cqzt", ""),  # 抽签状态
        "needs_payment": course.get("sfxyjf", "0") == "1",  # 是否需要缴费
        "needs_approval": course.get("sfxysh", "0") == "1",  # 是否需要审核
        "course_info": course.get("kcxx", ""),  # 课程信息（HTML）
        "class_number": course.get("kxh", ""),  # 课序号
    }


async def get_available_courses(
    session: Session,
    xn: str,
    xq: str,
    xnxq: str,
    dqxn: str,
    dqxq: str,
    dqxnxq: str,
    xkfsdm: str = "bx-b-b",  # 选课方式代码
    kkyx: str = "",  # 开课学院
    kclb: str = "",  # 课程类别
    xiaoqu: str = "",  # 校区
    gjz: str = "",  # 关键字搜索
    page_num: int = 1,
    page_size: int = 100,
) -> Dict:
    """获取可选课程列表

    Args:
        session: 用户会话
        xn: 选课学年
        xq: 选课学期
        xnxq: 选课学年学期
        dqxn: 当前学年
        dqxq: 当前学期
        dqxnxq: 当前学年学期
        xkfsdm: 选课方式代码 (bx-b-b/mooc-b-b/sztzk/zytzk/ggkrw)
        kkyx: 开课学院代码
        kclb: 课程类别代码
        xiaoqu: 校区代码
        gjz: 课程关键字
        page_num: 页码
        page_size: 每页数量
    """

    def _fetch():
        # 使用 queryKxrw 接口获取可选课程任务
        params = {
            "cxsfmt": "1",
            "p_pylx": "1",
            "mxpylx": "1",
            "p_sfgldjr": "0",
            "p_sfredis": "0",
            "p_sfsyxkgwc": "0",
            "p_xktjz": "",
            "p_chaxunxh": "",
            "p_gjz": gjz,
            "p_skjs": "",
            "p_xn": xn,
            "p_xq": xq,
            "p_xnxq": xnxq,
            "p_dqxn": dqxn,
            "p_dqxq": dqxq,
            "p_dqxnxq": dqxnxq,
            "p_xkfsdm": xkfsdm,
            "p_xiaoqu": xiaoqu,
            "p_kkyx": kkyx,
            "p_kclb": kclb,
            "p_xkxs": "",
            "p_dyc": "",
            "p_kkxnxq": "",
            "p_id": "",
            "p_sfhlctkc": "0",
            "p_sfhllrlkc": "0",
            "p_kxsj_xqj": "",
            "p_kxsj_ksjc": "",
            "p_kxsj_jsjc": "",
            "p_kcdm_js": "",
            "p_kcdm_cxrw": "",
            "p_kcdm_cxrw_zckc": "",
            "p_kc_gjz": gjz,
            "p_xzcxtjz_nj": "",
            "p_xzcxtjz_yx": "",
            "p_xzcxtjz_zy": "",
            "p_xzcxtjz_zyfx": "",
            "p_xzcxtjz_bj": "",
            "p_sfxsgwckb": "1",
            "p_skyy": "",
            "p_sfmxzj": "",
            "p_chaxunxkfsdm": "",
            "pageNum": str(page_num),
            "pageSize": str(page_size),
        }
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/Xsxk/queryKxrw",
            data=params,
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)

    # 调试日志：打印 BYYT 返回的原始数据结构
    logger.info(f"BYYT queryKxrw response keys: {result.keys() if isinstance(result, dict) else type(result)}")
    logger.info(f"BYYT queryKxrw xkfsdm={xkfsdm}, kxrwList type: {type(result.get('kxrwList', None)) if isinstance(result, dict) else 'N/A'}")
    # 如果没有kxrwList，打印完整响应
    if isinstance(result, dict) and 'kxrwList' not in result:
        logger.warning(f"BYYT queryKxrw no kxrwList, full response: {result}")

    # 解析返回数据
    courses = []
    total = 0
    if isinstance(result, dict):
        # kxrwList 包含可选课程任务列表
        kxrw_data = result.get("kxrwList", {})
        if isinstance(kxrw_data, dict):
            raw_courses = kxrw_data.get("list", [])
            total = kxrw_data.get("total", len(raw_courses))
        else:
            raw_courses = []

        for course in raw_courses:
            parsed = _parse_available_course(course)
            courses.append(parsed)

    return {
        "courses": courses,
        "total": total,
        "total_credits": sum(float(c.get("credits", 0)) for c in courses),
        "selection_method": xkfsdm,
    }


async def get_colleges(session: Session) -> List[Dict]:
    """获取开课学院列表（带缓存）"""
    cached = reference_data_cache.get("colleges")
    if cached is not None:
        return cached

    def _fetch():
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/queryKkyx",
            data="nodataqx=1",
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)

    colleges = []
    if isinstance(result, list):
        for item in result:
            colleges.append({
                "code": item.get("YXDM", "") or item.get("DM", ""),
                "name": item.get("YXMC", "") or item.get("MC", ""),
            })
    reference_data_cache.set("colleges", colleges)
    return colleges


async def get_course_categories(session: Session) -> List[Dict]:
    """获取课程类别列表（带缓存）"""
    cached = reference_data_cache.get("categories")
    if cached is not None:
        return cached

    def _fetch():
        params = {"dmbdm": "byyt_kclb", "mbmc": ""}
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/queryDmb",
            data=params,
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)

    categories = []
    if isinstance(result, list):
        for item in result:
            categories.append({
                "code": item.get("DM", ""),
                "name": item.get("MC", ""),
            })
    reference_data_cache.set("categories", categories)
    return categories


async def get_campuses(session: Session) -> List[Dict]:
    """获取校区列表（带缓存）"""
    cached = reference_data_cache.get("campuses")
    if cached is not None:
        return cached

    def _fetch():
        resp = session.client.post(
            "https://byyt.ustb.edu.cn/component/queryXiaoqu?pylx=3",
            data="",
        )
        _check_byyt_response(resp)
        resp.raise_for_status()
        return resp.json()

    result = await asyncio.to_thread(_fetch)

    campuses = []
    # 处理嵌套结构 {"code": 200, "content": [...]}
    if isinstance(result, dict) and "content" in result:
        items = result.get("content", [])
    elif isinstance(result, list):
        items = result
    else:
        items = []

    for item in items:
        campuses.append({
            "code": item.get("dm", "") or item.get("DM", ""),
            "name": item.get("mc", "") or item.get("MC", ""),
        })
    reference_data_cache.set("campuses", campuses)
    return campuses
