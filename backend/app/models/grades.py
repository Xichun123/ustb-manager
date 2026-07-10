from typing import Optional

from pydantic import BaseModel, Field


class GradeRecord(BaseModel):
    id: str
    term: str
    course_code: str
    course_name: str
    course_name_en: str = ""
    credit: float
    hours: Optional[float] = None
    score: str
    score_en: str = ""
    score_numeric: Optional[float] = None
    course_nature: str = ""
    course_category: str = ""
    college: str = ""
    exam_attempt: str = ""
    passed: Optional[bool] = None
    rank: Optional[int] = None


class GradePage(BaseModel):
    items: list[GradeRecord] = Field(default_factory=list)
    page: int
    page_size: int
    total: int


class GradeSummary(BaseModel):
    official_gpa: Optional[float] = None
    estimated_gpa: Optional[float] = None
    earned_credits: float = 0.0
    passed_courses: int = 0
    failed_courses: int = 0
