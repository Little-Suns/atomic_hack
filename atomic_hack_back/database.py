"""
Модуль конфигурации базы данных.
Содержит настройки подключения к PostgreSQL и фабрику сессий SQLAlchemy.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей SQLAlchemy.
    Все ORM модели должны наследоваться от этого класса.
    """
    pass


def get_db() -> Generator:
    """
    Генератор сессий базы данных для dependency injection в FastAPI.
    
    Yields:
        Session: Сессия SQLAlchemy для работы с БД
        
    Note:
        Автоматически закрывает сессию после использования
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
