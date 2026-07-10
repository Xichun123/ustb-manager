from typing import Optional

from pydantic import BaseModel, Field


class NoticeRecord(BaseModel):
    id: str
    title: str
    sender: str = ""
    sent_at: str = ""
    content: str = ""
    is_read: bool = False
    is_pinned: bool = False
    has_attachment: bool = False
    external_url: Optional[str] = None


class NoticePage(BaseModel):
    items: list[NoticeRecord] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
