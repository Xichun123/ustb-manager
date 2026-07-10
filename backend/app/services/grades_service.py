import asyncio
import logging
from typing import Dict, List, Optional
from app.byyt.academic import get_academic_terms
from app.byyt.grades import query_available_grade_terms
from app.byyt.grades import query_grades as query_current_grades
from app.byyt.profile import query_student_record, query_user_record
from app.byyt.progress import (
    get_student_academic_profile,
    query_credit_requirement_courses,
    query_plan_courses,
    query_required_course_status,
    query_student_plans,
)
from app.services.session_store import Session
from app.exceptions import BYYTSessionExpired
from app.cache import reference_data_cache

logger = logging.getLogger(__name__)


def _check_byyt_response(resp) -> None:
    """检查BYYT响应是否表示会话过期"""
    # 检查是否被重定向到登录页面
    if resp.url and "authentication" in str(resp.url):
        raise BYYTSessionExpired("BYYT session expired, redirected to login page")

    # 检查401状态码
    if resp.status_code == 401:
        raise BYYTSessionExpired("BYYT session expired, got 401")

    # 检查响应内容是否为HTML（登录页面）
    content_type = resp.headers.get("content-type", "")
    if "text/html" in content_type:
        raise BYYTSessionExpired("BYYT session expired, got HTML response instead of JSON")


async def get_grades(
    session: Session,
    page_num: int = 1,
    page_size: int = 100,
    xn: Optional[str] = None,
    xq: Optional[str] = None,
    kcxz: Optional[str] = None,
    kclb: Optional[str] = None,
) -> Dict:
    """兼容旧客户端的成绩响应，数据源使用当前个人成绩接口。"""
    page = await query_current_grades(
        session,
        year=xn,
        semester=xq,
        page=page_num,
        page_size=page_size,
    )
    records = page["items"]
    if kcxz:
        records = [record for record in records if record["course_nature"] == kcxz]
    if kclb:
        records = [record for record in records if record["course_category"] == kclb]

    grades = []
    for record in records:
        grades.append(
            {
                "xnxq": record["term"],
                "kcdm": record["course_code"],
                "kcmc": record["course_name"],
                "kcmc_en": record["course_name_en"],
                "xf": str(record["credit"]),
                "xs": "" if record["hours"] is None else str(record["hours"]),
                "xscj": record["score"],
                "zpcj": record["score"],
                "kcxzmc": record["course_nature"],
                "kclbmc": record["course_category"],
                "jsxm": "",
                "kkdw": record["college"],
                "bkcxbj": record["exam_attempt"],
            }
        )

    return {
        "list": grades,
        "total": len(grades) if kcxz or kclb else page["total"],
    }


async def get_student_info(session: Session) -> Dict:
    """获取学生基本信息。"""
    return await query_student_record(session)


async def get_user_info(session: Session) -> Dict:
    """获取当前用户完整信息（包含角色、权限）。"""
    return await query_user_record(session)


async def get_plan_course_list(session: Session, fah: str) -> List[Dict]:
    """获取培养方案课程列表。"""
    return await query_plan_courses(session, fah)


async def get_student_plan(session: Session) -> List[Dict]:
    """获取学生方案信息。"""
    plans = await query_student_plans(session)

    async def _enrich_plan(plan: Dict) -> Dict:
        if not isinstance(plan, dict):
            return plan

        fah = plan.get("fah")
        if not fah:
            plan["kclb_list"] = []
            return plan

        try:
            # 获取培养方案课程列表（总体要求）
            course_list = await get_plan_course_list(session, fah)

            # 获取已修课程信息（包含成绩）
            completed_courses = await query_xflbyq(session, fah, page_size=500)

            # 按课程代码建立已完成课程的映射
            completed_map = {}
            for course in completed_courses:
                kcdm = course.get("kcdm")
                if kcdm:
                    xscj = course.get("xscj") or course.get("zzcj")
                    if xscj:
                        try:
                            score = float(xscj) if str(xscj).replace(".", "").isdigit() else None
                            if score is not None and score >= 60:
                                completed_map[kcdm] = float(course.get("xf", 0) or 0)
                        except (ValueError, TypeError):
                            pass

            kclb_dict = {}
            for course in course_list:
                kclb = course.get("kclbmc", "其他")
                kcxz = course.get("kcxzmc", "")

                key = f"{kclb}_{kcxz}"
                if key not in kclb_dict:
                    kclb_dict[key] = {
                        "kclbmc": kclb,
                        "kcxzmc": kcxz,
                        "yqxdxf": 0.0,
                        "wcxf": 0.0,
                        "wwcxf": 0.0,
                    }

                xf = float(course.get("xf", 0) or 0)
                kclb_dict[key]["yqxdxf"] += xf

                # 检查该课程是否已完成
                kcdm = course.get("kcdm")
                if kcdm and kcdm in completed_map:
                    kclb_dict[key]["wcxf"] += completed_map[kcdm]

            # 计算未完成学分
            for item in kclb_dict.values():
                item["wwcxf"] = round(item["yqxdxf"] - item["wcxf"], 1)
                item["yqxdxf"] = round(item["yqxdxf"], 1)
                item["wcxf"] = round(item["wcxf"], 1)

            plan["kclb_list"] = list(kclb_dict.values())

        except Exception as exc:
            logger.warning("Failed to enrich plan %s: %s", fah, type(exc).__name__)
            plan["kclb_list"] = []

        return plan

    if plans:
        plans = await asyncio.gather(*[_enrich_plan(plan) for plan in plans])

    return plans


async def get_available_terms(session: Session) -> Dict:
    """查询可选学年学期（带缓存）。"""
    cached = reference_data_cache.get("grades_available_terms")
    if cached is not None:
        return cached

    result = await query_available_grade_terms(session)
    reference_data_cache.set("grades_available_terms", result)
    return result


async def get_required_course_status(
    session: Session,
    jzxnxq: Optional[str] = None,
) -> Dict:
    """查询必修课完成情况。"""
    return await query_required_course_status(session, jzxnxq)


async def get_term_list(session: Session) -> List[Dict]:
    """查询学年学期列表（带缓存）。"""
    cached = reference_data_cache.get("grades_term_list")
    if cached is not None:
        return cached

    terms = await get_academic_terms(session)
    reference_data_cache.set("grades_term_list", terms)
    return terms


def calculate_gpa(grades: List[Dict]) -> Dict:
    """计算GPA和学分统计

    GPA计算规则：
    - 90-100: 4.0
    - 85-89: 3.7
    - 82-84: 3.3
    - 78-81: 3.0
    - 75-77: 2.7
    - 72-74: 2.3
    - 68-71: 2.0
    - 64-67: 1.5
    - 60-63: 1.0
    - <60: 0
    """

    def score_to_gp(score: float) -> float:
        if score >= 90:
            return 4.0
        elif score >= 85:
            return 3.7
        elif score >= 82:
            return 3.3
        elif score >= 78:
            return 3.0
        elif score >= 75:
            return 2.7
        elif score >= 72:
            return 2.3
        elif score >= 68:
            return 2.0
        elif score >= 64:
            return 1.5
        elif score >= 60:
            return 1.0
        else:
            return 0.0

    total_credits = 0.0
    total_gp_credits = 0.0
    passed_credits = 0.0
    failed_count = 0

    for grade in grades:
        try:
            # 只统计正考成绩
            if grade.get("bkcxbj") != "正考":
                continue

            credit = float(grade.get("xf", 0))
            score_str = grade.get("xscj", "")

            # 跳过非数字成绩
            if not score_str or not score_str.replace(".", "").isdigit():
                continue

            score = float(score_str)
            gp = score_to_gp(score)

            total_credits += credit
            total_gp_credits += gp * credit

            if score >= 60:
                passed_credits += credit
            else:
                failed_count += 1

        except (ValueError, TypeError):
            continue

    gpa = total_gp_credits / total_credits if total_credits > 0 else 0.0

    return {
        "gpa": round(gpa, 2),
        "total_credits": round(total_credits, 1),
        "passed_credits": round(passed_credits, 1),
        "failed_count": failed_count,
    }


async def get_student_xs_info(session: Session) -> Dict:
    """获取学生信息（包含培养方案号 fah）。"""
    return await get_student_academic_profile(session)


async def query_xflbyq(
    session: Session,
    fah: str,
    page_size: int = 500,
) -> List[Dict]:
    """查询学分类别要求课程列表。"""
    return await query_credit_requirement_courses(
        session,
        fah,
        page_size=page_size,
    )


async def get_credit_completion_status(session: Session) -> Dict:
    """获取学分完成情况（从byyt系统）"""

    xs_info = await get_student_xs_info(session)
    fah = xs_info.get("fah")

    if not fah:
        return {"categories": []}

    xflbyq_list = await query_xflbyq(session, fah, page_size=500)

    kclb_list = xs_info.get("kclb_list", [])
    kclb_name_map = {item.get("dm"): item.get("mc", "其他") for item in kclb_list if item.get("dm")}

    kclb_dict = {}
    for course in xflbyq_list:
        kclbdm = course.get("kclbdm", "0")
        kclbmc = course.get("kclbmc")

        if not kclbmc:
            kclbmc = kclb_name_map.get(kclbdm, "其他")

        if kclbdm not in kclb_dict:
            kclb_dict[kclbdm] = {
                "category_code": kclbdm,
                "category_name": kclbmc,
                "required_credits": 0.0,
                "completed_credits": 0.0,
                "required_hours": 0,
                "completed_hours": 0,
                "courses": [],
            }

        xf = float(course.get("xf", 0) or 0)
        xs = int(course.get("xs", 0) or 0)
        kclb_dict[kclbdm]["required_credits"] += xf
        kclb_dict[kclbdm]["required_hours"] += xs

        xscj = course.get("xscj") or course.get("zzcj")
        if xscj:
            try:
                score = float(xscj) if str(xscj).replace(".", "").isdigit() else None
                if score is not None and score >= 60:
                    kclb_dict[kclbdm]["completed_credits"] += xf
                    kclb_dict[kclbdm]["completed_hours"] += xs
                    kclb_dict[kclbdm]["courses"].append(
                        {
                            "course_code": course.get("kcdm", ""),
                            "course_name": course.get("kcmc", ""),
                            "credits": xf,
                            "hours": xs,
                            "score": xscj,
                            "term": course.get("xnxqmc", ""),
                        }
                    )
            except (ValueError, TypeError):
                pass

    categories = []
    for cat in kclb_dict.values():
        cat["remaining_credits"] = round(cat["required_credits"] - cat["completed_credits"], 1)
        cat["remaining_hours"] = cat["required_hours"] - cat["completed_hours"]
        cat["required_credits"] = round(cat["required_credits"], 1)
        cat["completed_credits"] = round(cat["completed_credits"], 1)
        categories.append(cat)

    categories.sort(key=lambda x: x.get("category_code", ""))

    return {"categories": categories}
