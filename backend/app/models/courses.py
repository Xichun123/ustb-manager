from typing import Optional

from pydantic import BaseModel, Field


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


class CourseSelectionLog(BaseModel):
    id: str
    course_code: str = ""
    course_name: str = ""
    operation: str = ""
    operated_at: str = ""
    status: str = ""
    message: str = ""
