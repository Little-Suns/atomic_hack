# Atomic Hack - AI-Powered Presentation Generator

Интеллектуальная система для автоматической генерации презентаций PowerPoint с использованием LLM (Large Language Models), RAG (Retrieval-Augmented Generation) и компьютерного зрения.

## 📋 Содержание

- [Обзор](#обзор)
- [Архитектура](#архитектура)
- [Технологический стек](#технологический-стек)
- [Быстрый старт](#быстрый-старт)
- [Установка и настройка](#установка-и-настройка)
- [Использование](#использование)
- [API документация](#api-документация)
- [Структура проекта](#структура-проекта)
- [Разработка](#разработка)

## 🎯 Обзор

**Atomic Hack** - это полнофункциональная платформа для создания профессиональных презентаций с помощью искусственного интеллекта. Система анализирует загруженные документы, изображения и текстовые данные, чтобы автоматически генерировать структурированные презентации в формате PPTX.

### Основные возможности

- ✨ **Автоматическая генерация контента**: Создание слайдов на основе анализа документов
- 🎨 **Работа с шаблонами**: Поддержка пользовательских PPTX шаблонов
- 📊 **Умная визуализация**: Автоматическое создание графиков, таблиц и инфографики
- 🖼️ **Генерация изображений**: Интеграция с Kandinsky для создания иллюстраций
- 🔍 **OCR и анализ документов**: Обработка PDF, DOCX, изображений с извлечением текста
- 💬 **AI-ассистент**: Интерактивная доработка презентаций через чат
- 📁 **RAG система**: Векторный поиск по загруженным документам через Qdrant
- 🔄 **Экспорт в PPTX**: Конвертация презентаций в PPTX формат

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Upload Files │  │ Edit Slides  │  │ AI Assistant │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Auth Router  │  │ Presentation │  │ Files Router │       │
│  └──────────────┘  │    Router    │  └──────────────┘       │
│                    └──────────────┘                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Services Layer                           │   │
│  │  • LLM Service (OpenAI/Qwen)                         │   │
│  │  • RAG Service (Qdrant Vector DB)                    │   │
│  │  • PPTX Generator                                    │   │
│  │  • Image Generation (Kandinsky)                      │   │
│  │  • OCR Service                                       │   │
│  │  • S3 Storage Service                                │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
    ┌────────────────────────┼──────────────────────┐
    │                        │                      │
┌───▼──────┐        ┌────────▼──────┐       ┌───────▼──────┐
│PostgreSQL│        │    Qdrant     │       │  S3 Storage  │
│    DB    │        │  Vector DB    │       │  (Templates) │
└──────────┘        └───────────────┘       └──────────────┘
```

## 🛠️ Технологический стек

### Backend
- **Framework**: FastAPI (Python 3.13)
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL
- **Vector DB**: Qdrant
- **LLM**: OpenAI Comptable API (Qwen 3)
- **Document Processing**: 
  - python-pptx (PPTX generation)
  - PyPDF, PyMuPDF (PDF processing)
  - python-docx (Word processing)
  - Unstructured (document parsing)
- **Image Generation**: Kandinsky API
- **Storage**: S3 / MinIO
- **PDF Conversion**: Gotenberg
- **Package Manager**: uv

### Frontend
- **Framework**: React 18 + TypeScript
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Styling**: TailwindCSS
- **UI Components**: 
  - Headless UI
  - Lucide React (icons)
  - React Beautiful DnD (drag-and-drop)
- **Build Tool**: Vite

### DevOps
- **Containerization**: Docker + Docker Compose
- **Environment**: Python 3.13, Node.js 18+

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- (Опционально) Python 3.13+ и Node.js 18+ для локальной разработки

### Запуск через Docker

1. **Клонируйте репозиторий**:
```bash
git clone https://github.com/yourusername/atomic_hack.git
cd atomic_hack
```

2. **Настройте переменные окружения**:
```bash
# Backend
cp atomic_hack_back/.env.example atomic_hack_back/.env
# Отредактируйте atomic_hack_back/.env и укажите ваши API ключи

# Frontend
cp atomic_hack_front/.env.example atomic_hack_front/.env
```

3. **Настройте переменные окружения для production** (опционально):
```bash
# Для локальной разработки используйте значения по умолчанию
# Для production создайте .env в корне проекта:
cp .env.production.example .env

# И отредактируйте VITE_API_URL на ваш домен
VITE_API_URL=https://api.yourdomain.com
```

4. **Запустите все сервисы**:
```bash
docker-compose up -d
```

5. **Настройте MinIO (первый запуск)**:
- Откройте MinIO Console: http://localhost:9001
- Войдите: `minioadmin` / `minioadmin`
- Создайте bucket: `atomic-hack-presentations`

6. **Откройте приложение**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

### Остановка сервисов

```bash
docker-compose down
```

### Развертывание на сервере

Для production развертывания используйте **Dokploy** - self-hosted платформу для деплоя:

📖 **Полная инструкция**: [DEPLOYMENT.md](DEPLOYMENT.md)

## ⚙️ Установка и настройка

### Локальная разработка (без Docker)

#### Backend

1. **Установите Python 3.13+ и uv**:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. **Настройте переменные окружения**:
```bash
cd atomic_hack_back
cp .env.example .env
# Отредактируйте .env и укажите ваши API ключи
```

3. **Запустите PostgreSQL, Qdrant, Gotenberg и MinIO через Docker**:
```bash
# Из корневой директории проекта
docker-compose up -d postgres qdrant gotenberg minio
```

4. **Установите зависимости**:
```bash
cd atomic_hack_back
uv sync
```

5. **Запустите backend**:
```bash
# --host 0.0.0.0 делает сервер доступным на всех сетевых интерфейсах (важно для Linux)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend будет доступен на:
- Linux: http://0.0.0.0:8000
- macOS/Windows: http://localhost:8000

#### Frontend

1. **Установите зависимости**:
```bash
cd atomic_hack_front
npm install
```

2. **Настройте переменные окружения**:
```bash
cp .env.example .env
```

3. **Запустите frontend**:
```bash
npm run dev
```

### Конфигурация переменных окружения

#### Backend (.env)

```env
# Database (Linux: используйте 0.0.0.0, macOS/Windows: localhost)
DATABASE_URL=postgresql+psycopg://postgres:postgres@0.0.0.0:5432/atomic_hack

# OpenAI-compatible API (OpenAI, Cloud.ru, Qwen, и др.)
OPENAI_API_BASE=https://foundation-models.api.cloud.ru/v1
OPENAI_API_KEY=your-api-key-here
MODEL_NAME=Qwen/Qwen3-Next-80B-A3B-Instruct
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
LLM_TEMPERATURE=0.7

# Qdrant Vector Database (Linux: 0.0.0.0, macOS/Windows: localhost)
QDRANT_URL=http://0.0.0.0:6333
QDRANT_API_KEY=

# S3 Storage - MinIO (Linux: 0.0.0.0, macOS/Windows: localhost)
TEMPLATE_BUCKET_NAME=atomic-hack-presentations
S3_ENDPOINT_URL=http://0.0.0.0:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_USE_SSL=false
S3_ADDRESSING_STYLE=path

# Kandinsky Image Generation (опционально)
KANDINSKY_API_KEY=your-kandinsky-api-key
KANDINSKY_SECRET_KEY=your-kandinsky-secret-key

# Gotenberg PDF Converter (Linux: 0.0.0.0, macOS/Windows: localhost)
GOTENBERG_URL=http://0.0.0.0:3030

# OCR (опционально)
ENABLE_OCR=true
MIN_TEXT_LENGTH=1000

# Vision Model для OCR (опционально)
QWEN_VL_API_BASE=https://bothub.chat/api/v2/openai/v1
QWEN_VL_API_KEY=your-qwen-api-key
QWEN_VL_MODEL_NAME=qwen2.5-vl-32b-instruct
```

#### Frontend (.env)

```env
# Linux: используйте 0.0.0.0, macOS/Windows: localhost
VITE_API_URL=http://0.0.0.0:8000
VITE_API_MODE=api

# Для production используйте ваш домен:
# VITE_API_URL=https://api.yourdomain.com
```

## 📖 Использование

### 1. Создание новой презентации

1. Войдите в систему или зарегистрируйтесь
2. Нажмите "Создать новую презентацию"
3. Загрузите документы (PDF, DOCX, изображения)
4. Укажите название и тему презентации
5. Нажмите "Анализировать данные"
6. Просмотрите и отредактируйте структуру слайдов
7. Нажмите "Сгенерировать презентацию"
8. Скачайте готовую PPTX или PDF

### 2. Работа с шаблонами

1. Загрузите свой PPTX шаблон через интерфейс
2. Система автоматически извлечет стили и layouts
3. Новые презентации будут использовать ваш дизайн

### 3. Доработка через AI-ассистента

1. Откройте созданную презентацию
2. Используйте чат для запросов:
   - "Добавь слайд про технологии"
   - "Замени 'плохой' на 'хороший' везде"
   - "Удали 3-й слайд"
3. Система автоматически применит изменения

### 4. Ручное редактирование

1. В режиме редактирования измените:
   - Заголовки слайдов
   - Описания
   - Порядок слайдов (drag-and-drop)
2. Добавляйте или удаляйте слайды
3. Нажмите "Перегенерировать" для обновления контента

## 📚 API документация

### Основные эндпоинты

#### Аутентификация

```http
POST /api/registration
POST /api/login
```

#### Презентации

```http
GET    /api/getPresentations          # Список презентаций пользователя
POST   /api/createPresentation        # Создать новую презентацию
GET    /api/getPresentation/{id}      # Получить презентацию
DELETE /api/deletePresentation/{id}   # Удалить презентацию
POST   /api/changeSlidesInfo          # Изменить структуру слайдов
POST   /api/generatePresentation      # Генерация контента
POST   /api/presentationAssistantMessage  # Доработка через AI
GET    /api/getContent                # Получить контент слайдов
```

#### Файлы

```http
POST /api/uploadFiles        # Загрузить документы
POST /api/uploadTemplate     # Загрузить PPTX шаблон
GET  /api/downloadPptx       # Скачать PPTX
GET  /api/downloadPdf        # Скачать PDF
```

### Swagger документация

Полная интерактивная документация доступна по адресу:
```
http://localhost:8000/docs
```

## 📁 Структура проекта

```
atomic_hack/
├── atomic_hack_back/              # Backend приложение
│   ├── models/                    # SQLAlchemy модели
│   │   ├── user.py               # Модель пользователя
│   │   ├── presentation.py       # Модель презентации
│   │   └── slide.py              # Модель слайда
│   ├── routers/                   # API маршруты
│   │   ├── auth.py               # Аутентификация
│   │   ├── presentations.py      # Работа с презентациями
│   │   └── files.py              # Загрузка файлов
│   ├── schemas/                   # Pydantic схемы
│   │   ├── user.py
│   │   ├── presentation.py
│   │   └── slide.py
│   ├── services/                  # Бизнес-логика
│   │   ├── llm_service.py        # Интеграция с LLM
│   │   ├── rag_service.py        # RAG система (Qdrant)
│   │   ├── pptx_generator.py     # Генерация PPTX
│   │   ├── image_service.py      # Генерация изображений (Kandinsky)
│   │   ├── ocr_service.py        # OCR обработка
│   │   ├── s3_service.py         # S3 storage
│   │   └── pdf_converter.py      # PPTX → PDF (Gotenberg)
│   ├── main.py                    # Точка входа FastAPI
│   ├── config.py                  # Конфигурация логирования
│   ├── database.py                # Database setup
│   ├── pyproject.toml             # Python зависимости (uv)
│   └── .env                       # Переменные окружения
│
├── atomic_hack_front/             # Frontend приложение
│   ├── src/
│   │   ├── components/            # React компоненты
│   │   │   ├── FileUpload.tsx    # Загрузка файлов
│   │   │   ├── Header.tsx        # Шапка приложения
│   │   │   ├── SlideEditor.tsx   # Редактор слайдов
│   │   │   ├── PresentationPreview.tsx  # Превью презентации
│   │   │   ├── ProtectedRoute.tsx  # Защита роутов
│   │   │   └── StarRating.tsx    # Рейтинг
│   │   ├── pages/                 # Страницы
│   │   │   ├── LoginPage.tsx     # Вход/регистрация
│   │   │   ├── MainPage.tsx      # Создание презентации
│   │   │   └── ProfilePage.tsx   # Профиль пользователя
│   │   ├── contexts/              # React контексты
│   │   │   └── AuthContext.tsx   # Контекст аутентификации
│   │   ├── services/              # API клиенты
│   │   │   └── api.ts            # HTTP клиент
│   │   ├── App.tsx                # Главный компонент
│   │   └── main.tsx               # Точка входа
│   ├── package.json               # NPM зависимости
│   └── .env                       # Переменные окружения
│
├── docker-compose.yml             # Docker Compose конфигурация
├── Dockerfile.backend             # Backend Dockerfile
├── Dockerfile.frontend            # Frontend Dockerfile (multi-stage)
├── nginx.conf                     # Nginx конфигурация для frontend
├── .dockerignore                  # Исключения для Docker
├── README.md                      # Основная документация
└── DEPLOYMENT.md                  # Инструкция по развертыванию
```
