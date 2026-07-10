from typing import Optional

from pydantic import BaseModel, Field


class UserRole(BaseModel):
    code: str
    name: str = ""
    name_en: str = ""


class UserProfile(BaseModel):
    student_id: str
    name: str
    name_en: str = ""
    college: str = ""
    college_en: str = ""
    major: str = ""
    major_en: str = ""
    class_name: str = ""
    class_name_en: str = ""
    grade: str = ""
    grade_en: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    training_type: str = ""
    roles: list[UserRole] = Field(default_factory=list)
