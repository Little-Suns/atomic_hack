from typing import Optional

from pydantic import BaseModel, Field


class SlideCreate(BaseModel):
    """Схема для создания слайда"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    position: int = Field(..., ge=0)
    html_content: Optional[str] = None


class SlideUpdate(BaseModel):
    """Схема для обновления слайда"""
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    position: int = Field(..., ge=0)
    html_content: Optional[str] = None


class SlideGenerateRequest(BaseModel):
    """Запрос на генерацию структуры слайдов"""
    presentation_id: int
    topic: str = Field(..., min_length=1, description="Тема презентации")
    num_slides: int = Field(default=10, ge=1, le=50, description="Количество слайдов")
    use_context: bool = Field(default=True, description="Использовать загруженный контекст")


class SlidesUpdateRequest(BaseModel):
    """Запрос на обновление слайдов презентации"""
    presentation_id: int
    slides: list[SlideUpdate]
