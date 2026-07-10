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
