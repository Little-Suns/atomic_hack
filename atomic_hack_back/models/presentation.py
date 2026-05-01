"""
Модель презентации.
Хранит метаданные презентации, связи с пользователем и слайдами.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .slide import Slide
    from .user import User


class Presentation(Base):
    """
    ORM модель презентации.
    
    Attributes:
        id: Уникальный идентификатор презентации
        title: Название презентации
        user_id: ID владельца презентации
        template_bucket_id: S3 ключ загруженного PPTX шаблона
        context_files: JSON массив загруженных файлов для RAG
                      [{"filename": "...", "s3_key": "...", "uploaded_at": "..."}]
        rag_id: ID коллекции в Qdrant для векторного поиска
        slides: Список слайдов презентации (связь один-ко-многим)
        user: Владелец презентации
    """
    __tablename__ = "presentations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_bucket_id: Mapped[Optional[str]] = mapped_column(String(255))
    context_files: Mapped[Optional[str]] = mapped_column(Text)
    rag_id: Mapped[Optional[str]] = mapped_column(String(255))

    slides: Mapped[List["Slide"]] = relationship(
        "Slide",
        back_populates="presentation",
        cascade="all, delete-orphan",
        order_by="Slide.position",
    )
    user: Mapped["User"] = relationship("User", back_populates="presentations")
