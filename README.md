# Task Marketplace API

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL+PostGIS-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Celery-DC382D?style=for-the-badge&logo=redis&logoColor=white)

**Hyperlocal gig marketplace backend. Customers post tasks, providers find them nearby, payments go through escrow.**

</div>

---

## Architecture

<div align="center">

```
┌─────────────────────────────────────────────────────────┐
│                        CLIENT                           │
│              Mobile App / Web / Telegram                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                    FastAPI (async)                      │
│  /auth  /jobs  /payments  /profile  /reviews  /media   │
│              JWT (jose) + Argon2 passwords              │
└────┬─────────────┬──────────────┬───────────────────────┘
     │             │              │
┌────▼────┐  ┌─────▼─────┐  ┌────▼────────┐
│PostgreSQL│  │   Redis   │  │    MinIO    │
│+PostGIS  │  │           │  │  (S3-like)  │
│geo search│  │ Celery    │  │task photos  │
│migrations│  │ task queue│  │  avatars    │
│(Alembic) │  │           │  │            │
└─────────┘  └───────────┘  └────────────┘
```

</div>

---

## Features

| Feature | Details |
|---------|---------|
| **Geo search** | PostGIS radius queries — find tasks within N km |
| **Task lifecycle** | `open → matched → in_progress → completed / cancelled` |
| **Escrow payments** | Funds held until completion, then released to provider |
| **Real-time** | WebSocket notifications for status changes |
| **Background jobs** | Celery: notifications, payment processing, cleanup |
| **Media uploads** | MinIO for task photos and user avatars |
| **Reviews** | Mutual rating system after task completion |
| **Auth** | JWT access + refresh tokens, Argon2 hashing |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async) + Uvicorn |
| Database | PostgreSQL 15 + PostGIS 3.4 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Task queue | Celery + Redis |
| File storage | MinIO (S3-compatible) |
| Real-time | WebSocket |
| Auth | JWT (python-jose) + Argon2 |
| Containerization | Docker + docker-compose |
| API spec | OpenAPI / Swagger |

---

## Project structure

```
task-marketplace-api/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app + lifespan
│       ├── db.py                # Async SQLAlchemy engine
│       ├── security.py          # JWT + Argon2
│       ├── tasks.py             # Celery tasks
│       ├── realtime.py          # WebSocket manager
│       └── routers/
│           ├── auth.py          # Register, login, refresh
│           ├── jobs.py          # Create, search, match tasks
│           ├── payments.py      # Escrow flow
│           ├── profile.py       # User profiles
│           ├── reviews.py       # Ratings
│           └── media.py         # File uploads (MinIO)
├── db/init/
│   ├── 01_postgis.sql           # PostGIS extension
│   └── 02_schema.sql            # Initial schema
├── alembic/                     # DB migrations
├── tests/
├── docker-compose.yml
└── openapi.json                 # Full API spec
```

---

## Quick start

```bash
git clone https://github.com/Gotodataru/task-marketplace-api
cd task-marketplace-api
cp .env.example .env        # fill in your values
docker-compose up --build
```

API → `http://localhost:8000`  
Swagger docs → `http://localhost:8000/docs`

---

## Environment variables

```env
JWT_SECRET=your_secret_here
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

---

## Status

Core backend ~70% complete. Auth, task lifecycle, geo search, escrow payments, real-time — implemented. Frontend not included.
