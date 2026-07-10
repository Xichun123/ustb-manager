from typing import Optional

from pydantic import BaseModel, Field


class CalendarMonthMetadata(BaseModel):
    year: Optional[int] = None
    month: int = Field(..., ge=1, le=12)
    label: str = ""
    days_in_month: Optional[int] = None


class CalendarDate(BaseModel):
    date: str
    week: Optional[int] = None


class AcademicCalendar(BaseModel):
    term: str
    month: CalendarMonthMetadata
    dates: list[CalendarDate] = Field(default_factory=list)


class AcademicProgress(BaseModel):
    cutoff_term: Optional[str] = None
    required_courses: Optional[int] = None
    completed_courses: Optional[int] = None
    remaining_courses: Optional[int] = None
    required_credits: Optional[float] = None
    completed_credits: Optional[float] = None
    remaining_credits: Optional[float] = None
    credit_score: Optional[float] = None
    major_rank: Optional[int] = None
    major_student_count: Optional[int] = None


class AcademicProgressModule(BaseModel):
    id: str
    parent_id: str = ""
    name: str
    name_en: str = ""
    module_type: str = ""
    course_category_code: str = ""
    course_nature_code: str = ""
    required_groups: Optional[int] = None
    completed_groups: Optional[int] = None
    required_courses: Optional[int] = None
    completed_courses: Optional[int] = None
    required_hours: Optional[float] = None
    completed_hours: Optional[float] = None
    required_credits: Optional[float] = None
    completed_credits: Optional[float] = None
    passed: Optional[bool] = None
    is_required: Optional[bool] = None
    remark: str = ""
    children: list["AcademicProgressModule"] = Field(default_factory=list)


class AcademicProgressModules(BaseModel):
    is_available: bool
    items: list[AcademicProgressModule] = Field(default_factory=list)


class AcademicProgressCategory(BaseModel):
    code: str
    name: str
    name_en: str = ""
    course_nature_code: str = ""
    course_nature: str = ""
    required_credits: Optional[float] = None
    completed_credits: Optional[float] = None
    remaining_credits: Optional[float] = None
    convertible_credits: Optional[float] = None
    converted_credits: Optional[float] = None
    remark: str = ""


class AcademicProgressCourse(BaseModel):
    id: str
    course_code: str
    course_name: str
    course_name_en: str = ""
    term: str = ""
    credits: Optional[float] = None
    hours: Optional[float] = None
    score: str = ""
    passed: Optional[bool] = None
    counts_toward_requirement: Optional[bool] = None
    is_required: Optional[bool] = None
    course_nature_code: str = ""
    course_nature: str = ""
    course_category_code: str = ""
    course_category: str = ""
    college: str = ""
    module_id: str = ""
    module_name: str = ""
    major_direction_code: str = ""
    major_direction: str = ""


class AcademicProgressCourses(BaseModel):
    is_available: bool
    categories: list[AcademicProgressCategory] = Field(default_factory=list)
    courses: list[AcademicProgressCourse] = Field(default_factory=list)


class AcademicWarningCourse(BaseModel):
    course_code: str
    course_name: str
    hours: Optional[float] = None
    credits: Optional[float] = None
    term: str = ""
    score: str = ""
    course_category: str = ""
    course_nature: str = ""
    exam_attempt: str = ""


class AcademicWarning(BaseModel):
    term: str
    has_warning: bool
    is_published: bool
    is_acknowledged: bool
    acknowledged_at: Optional[str] = None
    counted_credits: Optional[float] = None
    earned_courses: list[AcademicWarningCourse] = Field(default_factory=list)
    unearned_courses: list[AcademicWarningCourse] = Field(default_factory=list)
