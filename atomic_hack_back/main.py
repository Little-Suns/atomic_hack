"""
Главный модуль FastAPI приложения.
Инициализирует приложение, подключает middleware, роутеры и настраивает БД.
"""

from dotenv import load_dotenv
from pathlib import Path
import logging

dotenv_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

from config import setup_logging
setup_logging()
logger = logging.getLogger("app")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models.user
import models.presentation
import models.slide
from routers import auth, presentations, files

app = FastAPI()

logger.info("FastAPI приложение инициализировано")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://atomichack.junkjammerservice.me",
        "http://localhost:5173",
        "http://localhost:3030"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware добавлен")

Base.metadata.create_all(bind=engine)
logger.info("База данных инициализирована")

app.include_router(auth.router, prefix="/api")
app.include_router(presentations.router, prefix="/api")
app.include_router(files.router, prefix="/api")

logger.info("Все routers зарегистрированы")
