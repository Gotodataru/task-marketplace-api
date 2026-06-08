
# backend/app/routers/auth.py
"""
Реальный auth с Postgres:
- /auth/register: пишет пользователя в таблицу users (если уже есть — возвращает существующий id)
- /auth/login: проверяет пароль по хэшу из БД и отдаёт JWT
- При первом запуске аккуратно создаёт таблицу, если её нет (id, email unique, ...).
Схема совместима с простым MVP.
"""

from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Optional, Dict, Any
import os
import bcrypt
import psycopg2
import psycopg2.extras

from ..security import create_access_token, get_current_user_id

router = APIRouter()

# --- DB env (совпадает с docker-compose) ---
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secret")

def _get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

def _ensure_schema():
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id              SERIAL PRIMARY KEY,
        email           TEXT UNIQUE NOT NULL,
        full_name       TEXT,
        role            TEXT,
        password_hash   TEXT NOT NULL,
        can_take_jobs   BOOLEAN NOT NULL DEFAULT FALSE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with _get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()

def _merge(body: Optional[dict], **defaults) -> dict:
    data = {**defaults}
    body = body or {}
    for k, v in body.items():
        if v is not None:
            data[k] = v
    return data

def _hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def _verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

@router.post("/register")
async def register(
    email: Optional[str] = None,
    password: Optional[str] = None,
    full_name: Optional[str] = None,
    role: Optional[str] = "customer",
    body: Optional[dict] = Body(default=None),
):
    """
    Принимает:
      - query: ?email=..&password=..&full_name=..&role=..
      - или JSON: {"email": "...", "password": "...", "full_name": "...", "role": "..."}
    Возвращает:
      {"id": int, "email": str, "created": true}  — если добавили
      или {"id": int, "email": str, "exists": true} — если уже есть
    """
    _ensure_schema()

    data = _merge(body, email=email, password=password, full_name=full_name, role=role)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    full_name = data.get("full_name")
    role = (data.get("role") or "customer").strip().lower()

    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")

    with _get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # Пытаемся вставить; если уже есть — берём существующий id
        try:
            cur.execute(
                """
                INSERT INTO users (email, full_name, role, password_hash, can_take_jobs)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING id, xmax = 0 AS inserted;
                """,
                (email, full_name, role, _hash_password(password), False),
            )
            row = cur.fetchone()
            conn.commit()
            user_id = int(row["id"])
            inserted = bool(row["inserted"])
        except psycopg2.errors.UndefinedTable:
            # На всякий случай (если гонка до _ensure_schema)
            conn.rollback()
            _ensure_schema()
            cur.execute(
                """
                INSERT INTO users (email, full_name, role, password_hash, can_take_jobs)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING id, xmax = 0 AS inserted;
                """,
                (email, full_name, role, _hash_password(password), False),
            )
            row = cur.fetchone()
            conn.commit()
            user_id = int(row["id"])
            inserted = bool(row["inserted"])

    if inserted:
        return {"id": user_id, "email": email, "created": True}
    else:
        return {"id": user_id, "email": email, "exists": True}

@router.post("/login")
async def login(
    email: Optional[str] = None,
    password: Optional[str] = None,
    body: Optional[dict] = Body(default=None),
):
    """
    Принимает:
      - query: ?email=..&password=..
      - или JSON: {"email": "...", "password": "..."}
    Возвращает:
      {"access_token": "...", "token_type": "bearer"}
    """
    data = _merge(body, email=email, password=password)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")

    _ensure_schema()
    with _get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT id, password_hash FROM users WHERE email=%s", (email,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not _verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    uid = int(row["id"])
    token = create_access_token(str(uid))
    return {"access_token": token, "token_type": "bearer", "user_id": uid}


@router.get("/me")
async def me(user_id: int = Depends(get_current_user_id)):
    """Профиль текущего пользователя (нужен Bearer-токен из /auth/login)."""
    _ensure_schema()
    with _get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            "SELECT id, email, full_name, role, can_take_jobs, created_at FROM users WHERE id=%s",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return dict(row)
