from typing import Optional

from pydantic import BaseModel, Field


class ScheduleCourse(BaseModel):
    course_id: str
    course_code: str = ""
    course_name: str
    course_name_en: str = ""
    teacher: str = ""
    weekday: int = Field(..., ge=1, le=7)
    start_period: int = Field(..., ge=1)
    end_period: int = Field(..., ge=1)
    weeks: list[int] = Field(default_factory=list)
    week_text: str = ""
    location: str = ""
    campus: str = ""
    period_text: str = ""
    task_code: str = ""


class ScheduleView(BaseModel):
    term: str
    week: Optional[int] = None
    dates: dict[int, str] = Field(default_factory=dict)
    items: list[ScheduleCourse] = Field(default_factory=list)
