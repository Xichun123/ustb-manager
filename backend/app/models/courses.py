from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CourseSelectionTerm(BaseModel):
    year: str
    semester: str
    code: str


class CourseSelectionMethod(BaseModel):
    code: str
    name: str
    name_en: str = ""
    mode: str = ""


class CourseReferenceOption(BaseModel):
    code: str
    name: str


class CourseSelectionCapabilities(BaseModel):
    course_query: bool = True
    selected_query: bool = True
    cart_query: bool = True
    log_query: bool = True
    preflight: bool = True
    writes_enabled: bool = False


class CourseSelectionContext(BaseModel):
    term: CourseSelectionTerm
    methods: list[CourseSelectionMethod] = Field(default_factory=list)
    colleges: list[CourseReferenceOption] = Field(default_factory=list)
    categories: list[CourseReferenceOption] = Field(default_factory=list)
    campuses: list[CourseReferenceOption] = Field(default_factory=list)
    capabilities: CourseSelectionCapabilities


class CourseSelectionRecord(BaseModel):
    course_id: str
    selection_id: Optional[str] = None
    course_code: str = ""
    course_name: str = ""
    course_name_en: str = ""
    course_nature: str = ""
    course_category: str = ""
    credits: float = 0
    hours: Optional[float] = None
    method: str = ""
    college: str = ""
    campus: str = ""
    capacity: Optional[int] = None
    selected_count: Optional[int] = None
    internal_capacity: Optional[int] = None
    internal_selected_count: Optional[int] = None
    external_capacity: Optional[int] = None
    external_selected_count: Optional[int] = None
    teacher: str = ""
    schedule_time: str = ""
    schedule_location: str = ""
    selection_status: str = ""
    is_selected: bool = False


class CourseSelectionPage(BaseModel):
    items: list[CourseSelectionRecord] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    total_credits: float
    method: str


class SelectedCoursePage(BaseModel):
    items: list[CourseSelectionRecord] = Field(default_factory=list)
    total: int
    total_credits: float


class CoursePreflightRequest(BaseModel):
    course_id: str
    selection_id: Optional[str] = None
    method: str = "bx-b-b"


class CoursePreflightResponse(BaseModel):
    allowed: bool
    status: Literal["clear", "conflict", "blocked", "unknown"]
    message: str = ""


class CourseWriteRequest(BaseModel):
    course_id: str
    selection_id: Optional[str] = None
    method: str = "bx-b-b"


class CourseWriteResponse(BaseModel):
    success: bool
    status: Literal["success", "failed"]
    message: str = ""


class CourseSnatchCourseRequest(BaseModel):
    course_id: str = Field(min_length=1, max_length=128)
    selection_id: Optional[str] = Field(default=None, max_length=128)
    course_code: str = Field(default="", max_length=64)
    course_name: str = Field(default="", max_length=256)
    method: str = Field(default="zytzk-b-b", min_length=1, max_length=64)


class CourseSnatchTaskRequest(BaseModel):
    courses: list[CourseSnatchCourseRequest] = Field(min_length=1, max_length=10)
    start_at: datetime
    retry_interval_seconds: float = Field(default=1.0, ge=0.1, le=30)

    @field_validator("courses")
    @classmethod
    def require_unique_courses(
        cls,
        value: list[CourseSnatchCourseRequest],
    ) -> list[CourseSnatchCourseRequest]:
        course_ids = [course.course_id for course in value]
        if len(course_ids) != len(set(course_ids)):
            raise ValueError("courses must not contain duplicate course_id values")
        return value

    @field_validator("start_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("start_at must include a timezone")
        return value


class CourseSnatchItem(BaseModel):
    course_id: str
    selection_id: Optional[str] = None
    course_code: str = ""
    course_name: str = ""
    method: str
    status: Literal["pending", "retrying", "success", "failed"] = "pending"
    attempts: int = 0
    message: str = ""
    error_type: Optional[
        Literal["conflict", "full", "not_open", "not_eligible", "already_selected", "unknown"]
    ] = None


class CourseSnatchTask(BaseModel):
    task_id: str
    status: Literal[
        "scheduled",
        "running",
        "completed",
        "completed_with_errors",
        "stopped",
        "failed",
    ]
    start_at: datetime
    retry_interval_seconds: float
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    message: str = ""
    items: list[CourseSnatchItem] = Field(default_factory=list)


class CourseAnnouncement(BaseModel):
    id: str
    title: str
    content: str = ""
    published_at: str = ""


class CourseSelectionLog(BaseModel):
    id: str
    course_code: str = ""
    course_name: str = ""
    operation: str = ""
    operated_at: str = ""
    status: str = ""
    message: str = ""
