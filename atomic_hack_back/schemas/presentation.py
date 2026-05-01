from typing import List, Optional

from pydantic import BaseModel, Field


class SlideRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    position: int
    content_json: Optional[str] = None

    class Config:
        from_attributes = True


class PresentationRead(BaseModel):
    id: int
    title: str
    user_id: int
    template_bucket_id: Optional[str] = None
    context_files: Optional[str] = None
    rag_id: Optional[str] = None
    slides: List[SlideRead] = Field(default_factory=list)

    class Config:
        from_attributes = True
