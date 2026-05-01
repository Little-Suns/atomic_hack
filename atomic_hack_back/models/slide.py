"""
Модель слайда презентации.
Хранит контент и метаданные отдельного слайда.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .presentation import Presentation


class Slide(Base):
    """
    ORM модель слайда.
    
    Attributes:
        id: Уникальный идентификатор слайда
        presentation_id: ID родительской презентации
        title: Заголовок слайда
        description: Краткое описание содержимого слайда
        position: Позиция слайда в презентации (начиная с 1)
        content_json: JSON со структурированным контентом слайда
                     {"blocks": [{"type": "text/chart/table/image", "data": {...}}]}
        presentation: Родительская презентация
    """
    __tablename__ = "slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[Optional[str]] = mapped_column(Text)

    presentation: Mapped["Presentation"] = relationship("Presentation", back_populates="slides")
