"""
Модель пользователя системы.
Хранит информацию об аутентификации и связь с презентациями.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .presentation import Presentation


class User(Base):
    """
    ORM модель пользователя.
    
    Attributes:
        id: Уникальный идентификатор пользователя
        email: Email адрес (используется для входа)
        hashed_password: Хешированный пароль (bcrypt)
        created_at: Дата и время регистрации
        presentations: Список презентаций пользователя (связь один-ко-многим)
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    presentations: Mapped[List["Presentation"]] = relationship(
        "Presentation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
