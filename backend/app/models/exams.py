from typing import Optional

from pydantic import BaseModel, Field


class ExamRecord(BaseModel):
    id: str
    term: str
    course_code: str
    course_name: str
    course_name_en: str = ""
    exam_type: str = ""
    exam_type_en: str = ""
    date: str = ""
    date_display: str = ""
    time: str = ""
    week: Optional[int] = None
    weekday: Optional[int] = Field(None, ge=1, le=7)
    weekday_name: str = ""
    start_period: Optional[int] = None
    end_period: Optional[int] = None
    building: str = ""
    room: str = ""
    seat_number: Optional[str] = None
    college: str = ""
    remark: str = ""


class ExamPage(BaseModel):
    items: list[ExamRecord] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
