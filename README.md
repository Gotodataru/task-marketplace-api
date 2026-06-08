# Task Marketplace API

Backend for a hyperlocal gig marketplace. Customers post tasks with geolocation, providers find nearby tasks, work is tracked through a status machine, payments go through escrow.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async) |
| Database | PostgreSQL 15 + PostGIS |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Background tasks | Celery + Redis |
| File storage | MinIO (S3-compatible) |
| Real-time | WebSocket |
| Auth | JWT (jose) + Argon2 password hashing |
| Containerization | Docker + docker-compose |

## Features

- **Geo-based task discovery** — PostGIS radius queries, tasks sorted by distance
- **Status machine** — `open → matched → in_progress → completed / cancelled`
- **Escrow payments** — funds held until task completion, then released to provider
- **Real-time updates** — WebSocket notifications for task status changes
- **Background jobs** — Celery tasks for notifications, payment processing, cleanup
- **Media uploads** — MinIO integration for task photos and user avatars
- **Reviews** — mutual rating system after task completion

## Project structure

```
taskservis/
├── backend/
│   └── app/
│       ├── main.py           # FastAPI app + lifespan
│       ├── db.py             # Async SQLAlchemy engine
│       ├── security.py       # JWT + Argon2
│       ├── tasks.py          # Celery tasks
│       ├── realtime.py       # WebSocket manager
│       └── routers/
│           ├── auth.py       # Register, login, refresh
│           ├── jobs.py       # Create, search, match tasks
│           ├── payments.py   # Escrow flow
│           ├── profile.py    # User profiles
│           ├── reviews.py    # Ratings
│           └── media.py      # File uploads
├── db/
│   └── init/
│       ├── 01_postgis.sql    # PostGIS extension
│       └── 02_schema.sql     # Initial schema
├── alembic/                  # Migrations
├── tests/
├── docker-compose.yml
└── openapi.json              # Full API spec
```

## Quick start

```bash
git clone https://github.com/Gotodataru/task-marketplace-api
cd task-marketplace-api
cp .env.example .env
docker-compose up --build
```

API available at `http://localhost:8000`  
Docs at `http://localhost:8000/docs`

## Environment variables

```env
JWT_SECRET=your_secret_here
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## Status

MVP backend ~70% complete. Core flows (auth, task lifecycle, geo search, payments) implemented. Frontend not included.
