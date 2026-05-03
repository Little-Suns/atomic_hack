# Atomic Hack — AI Presentation Generator

Atomic Hack is a full-stack app that generates, edits, and exports presentation decks with AI support.  
It combines FastAPI, React, PostgreSQL, Qdrant, and S3-compatible storage to build slide structures from user prompts and uploaded context files.

## Why this project

- Generates slide outlines and structured slide content with LLMs
- Supports context-aware generation via RAG (Qdrant)
- Allows template-based export to **PPTX** and **PDF**
- Includes an assistant flow for targeted slide rewrites

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | React 18, TypeScript, Vite, TailwindCSS |
| Backend | FastAPI, SQLAlchemy, Uvicorn |
| Data | PostgreSQL, Qdrant |
| Storage | S3 / MinIO |
| AI services | OpenAI-compatible API, Kandinsky (optional) |
| Infra | Docker Compose |

## Repository structure

```text
.
├── atomic_hack_back/     # FastAPI backend
├── atomic_hack_front/    # React frontend
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── DEPLOYMENT.md
```

## Quick start (Docker)

1. Clone the repository:

```bash
git clone https://github.com/Little-Suns/atomic_hack.git
cd atomic_hack
```

2. Create env files:

```bash
cp atomic_hack_back/.env.example atomic_hack_back/.env
cp atomic_hack_front/.env.example atomic_hack_front/.env
```

3. Start services:

```bash
docker-compose up -d
```

4. Open:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

## Local development (without full Docker app)

### Backend

```bash
cd atomic_hack_back
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd atomic_hack_front
npm install
npm run dev
```

## Environment notes

- Backend env template: `atomic_hack_back/.env.example`
- Frontend env template: `atomic_hack_front/.env.example`
- Make sure external services (database/vector DB/storage/LLM APIs) are configured before generation flows.

## Deployment

Production deployment instructions are in [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

If you use this project as a portfolio sample, focus demos on:
1. Context file upload + slide generation flow  
2. AI-assisted slide updates  
3. PPTX/PDF export pipeline
