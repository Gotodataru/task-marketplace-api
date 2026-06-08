# backend/app/routers/jobs.py — гиперлокальные поручения (задания рядом, гео-поиск)
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import os
import logging
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError, errors

from ..security import get_current_user_id
from ..realtime import broadcast_chat

logger = logging.getLogger("jobs")
router = APIRouter()

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "app")
DB_PASS = os.getenv("DB_PASSWORD", "secret")

JOB_OPEN_DEFAULT_HOURS = int(os.getenv("JOB_OPEN_DEFAULT_HOURS", "48"))


def db_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )


DDL_JOBS = """
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    price_rub INTEGER NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    customer_id INTEGER,
    provider_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
"""


def ensure_postgis(cur) -> None:
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


def ensure_jobs_table(retries: int = 20, delay: float = 1.0) -> None:
    last_err = None
    for _ in range(retries):
        try:
            with db_conn() as conn:
                with conn.cursor() as cur:
                    ensure_postgis(cur)
                    cur.execute(DDL_JOBS)
                    conn.commit()
            return
        except OperationalError as e:
            last_err = e
            import time as _t

            _t.sleep(delay)
        except Exception as e:
            last_err = e
            import time as _t

            _t.sleep(delay)
    logger.error("ensure_jobs_table failed: %s", last_err)
    raise last_err if last_err else RuntimeError("ensure_jobs_table: unknown error")


def migrate_jobs_table() -> None:
    """Добавляем недостающие колонки (в т.ч. под ТЗ: категории поручений, описание, адрес)."""
    alters = [
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE jobs ALTER COLUMN title DROP DEFAULT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS price_rub INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE jobs ALTER COLUMN price_rub DROP DEFAULT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ALTER TABLE jobs ALTER COLUMN lat DROP DEFAULT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ALTER TABLE jobs ALTER COLUMN lon DROP DEFAULT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open'",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS customer_id INTEGER",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS provider_id INTEGER",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'other'",
        "ALTER TABLE jobs ALTER COLUMN category DROP DEFAULT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ",
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ",
    ]
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                ensure_postgis(cur)
                for stmt in alters:
                    try:
                        cur.execute(stmt)
                    except Exception as e:
                        logger.debug("migrate step skipped: %s", e)
                conn.commit()
    except Exception as e:
        logger.warning("migrate_jobs_table skipped/failed: %s", e)


DDL_MESSAGES = """
CREATE TABLE IF NOT EXISTS job_messages (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS job_messages_job_id_idx ON job_messages(job_id);
"""


def migrate_messages_table() -> None:
    migrate_jobs_table()
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                for stmt in DDL_MESSAGES.strip().split(";"):
                    s = stmt.strip()
                    if s:
                        try:
                            cur.execute(s)
                        except Exception as e:
                            logger.debug("messages ddl: %s", e)
                conn.commit()
    except Exception as e:
        logger.warning("migrate_messages_table: %s", e)


try:
    ensure_jobs_table(retries=3, delay=0.5)
except Exception as e:
    logger.warning("jobs table not ensured on import (will retry on demand): %s", e)

# Категории поручений (MVP по ТЗ). Старые значения маппятся в other при выдаче.
Category = Literal[
    "small_repair",
    "carry",
    "buy",
    "clean",
    "other",
    "walk",
    "boarding",
    "grooming",
]

DEFAULT_TITLE = "Задание"
DEFAULT_PRICE = 0
DEFAULT_LAT = 55.751244
DEFAULT_LON = 37.618423
DEFAULT_CATEGORY: Category = "other"


class JobCreate(BaseModel):
    category: Category = DEFAULT_CATEGORY
    title: str = Field(DEFAULT_TITLE, min_length=1)
    description: Optional[str] = None
    address: Optional[str] = None
    price_rub: int = Field(DEFAULT_PRICE, ge=0)
    lat: float = DEFAULT_LAT
    lon: float = DEFAULT_LON
    expires_hours: Optional[int] = Field(
        None, ge=1, le=720, description="Через сколько часов снять с поиска (по умолчанию из env)"
    )


class JobOut(BaseModel):
    id: int
    title: str
    price_rub: int
    lat: float
    lon: float
    status: str
    category: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    customer_id: Optional[int] = None
    provider_id: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    distance_m: Optional[float] = None


class AssignBody(BaseModel):
    provider_id: int = Field(..., ge=1)


class MessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class MessageOut(BaseModel):
    id: int
    job_id: int
    sender_id: int
    content: str
    created_at: Optional[str] = None


async def parse_job_create(request: Request) -> JobCreate:
    try:
        if request.headers.get("content-type", "").lower().startswith("application/json"):
            data = await request.json()
            if isinstance(data, dict):
                return JobCreate(**data)
    except Exception:
        pass

    q = request.query_params
    if any(
        k in q
        for k in (
            "title",
            "price_rub",
            "lat",
            "lon",
            "category",
            "description",
            "address",
            "expires_hours",
        )
    ):
        try:
            return JobCreate(
                title=q.get("title", DEFAULT_TITLE),
                description=q.get("description"),
                address=q.get("address"),
                price_rub=int(q["price_rub"]) if "price_rub" in q else DEFAULT_PRICE,
                lat=float(q["lat"]) if "lat" in q else DEFAULT_LAT,
                lon=float(q["lon"]) if "lon" in q else DEFAULT_LON,
                category=q.get("category", DEFAULT_CATEGORY),  # type: ignore[arg-type]
                expires_hours=int(q["expires_hours"]) if "expires_hours" in q else None,
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Bad query params types")

    return JobCreate()


def _ts(v) -> Optional[str]:
    if v is None:
        return None
    return v.isoformat() if hasattr(v, "isoformat") else str(v)


def row_to_jobout(row: dict, distance_m: Optional[float] = None) -> JobOut:
    return JobOut(
        id=row["id"],
        title=row["title"],
        price_rub=row["price_rub"],
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        status=row["status"],
        category=row.get("category"),
        description=row.get("description"),
        address=row.get("address"),
        customer_id=row.get("customer_id"),
        provider_id=row.get("provider_id"),
        started_at=_ts(row.get("started_at")),
        completed_at=_ts(row.get("completed_at")),
        created_at=_ts(row.get("created_at")),
        expires_at=_ts(row.get("expires_at")),
        distance_m=distance_m,
    )


def _select_cols() -> str:
    return "id, title, price_rub, lat, lon, status, category, description, address, customer_id, provider_id, started_at, completed_at, created_at, expires_at"


@router.post("/", response_model=JobOut, status_code=201)
async def create_job(
    request: Request, user_id: int = Depends(get_current_user_id)
):
    data = await parse_job_create(request)

    try:
        ensure_jobs_table(retries=1, delay=0.0)
    except Exception:
        pass
    migrate_jobs_table()

    hours = (
        data.expires_hours
        if data.expires_hours is not None
        else JOB_OPEN_DEFAULT_HOURS
    )
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    sql = f"""
        INSERT INTO jobs (title, price_rub, lat, lon, category, status, customer_id, description, address, expires_at)
        VALUES (%s, %s, %s, %s, %s, 'open', %s, %s, %s, %s)
        RETURNING {_select_cols()}
    """
    params = (
        data.title,
        data.price_rub,
        data.lat,
        data.lon,
        data.category,
        user_id,
        data.description,
        data.address,
        expires_at,
    )

    try:
        with db_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                conn.commit()
                return row_to_jobout(row)

    except errors.UndefinedTable:
        ensure_jobs_table(retries=10, delay=0.5)
        migrate_jobs_table()
        with db_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                conn.commit()
                return row_to_jobout(row)

    except Exception as e:
        logger.exception("create_job failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal error while creating job")


@router.get("/near", response_model=List[JobOut])
async def jobs_near(lat: float, lon: float, radius_m: int = 2000):
    """Открытые задания в радиусе (PostGIS ST_DWithin, метры)."""
    migrate_jobs_table()
    sql = f"""
        SELECT {_select_cols()},
               ST_Distance(
                 ST_SetSRID(ST_MakePoint(jobs.lon, jobs.lat), 4326)::geography,
                 ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
               ) AS distance_m
        FROM jobs
        WHERE status = 'open'
          AND ST_DWithin(
            ST_SetSRID(ST_MakePoint(jobs.lon, jobs.lat), 4326)::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
          )
        ORDER BY distance_m ASC
    """
    # параметры: для SELECT dist — lon, lat; для WHERE — lon, lat, radius_m
    params = (lon, lat, lon, lat, radius_m)
    try:
        with db_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
    except Exception as e:
        logger.warning("jobs_near postgis failed, fallback bbox: %s", e)
        return _jobs_near_fallback(lat, lon, radius_m)

    out = []
    for r in rows:
        dm = float(r["distance_m"]) if r.get("distance_m") is not None else None
        out.append(row_to_jobout(r, distance_m=dm))
    return out


@router.get("/mine", response_model=List[JobOut])
async def jobs_mine(
    user_id: int = Depends(get_current_user_id),
    role: str = "both",
    status: Optional[str] = None,
):
    """Мои задания: как заказчик и/или исполнитель."""
    migrate_jobs_table()
    if role not in ("customer", "provider", "both"):
        raise HTTPException(status_code=400, detail="role must be customer|provider|both")
    parts = []
    params: List = []
    if role == "customer":
        parts.append("customer_id = %s")
        params.append(user_id)
    elif role == "provider":
        parts.append("provider_id = %s")
        params.append(user_id)
    else:
        parts.append("(customer_id = %s OR provider_id = %s)")
        params.extend([user_id, user_id])
    where = " AND ".join(parts)
    if status:
        where += " AND status = %s"
        params.append(status)
    sql = f"SELECT {_select_cols()} FROM jobs WHERE {where} ORDER BY id DESC LIMIT 200"
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    return [row_to_jobout(r) for r in rows]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int):
    migrate_jobs_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"SELECT {_select_cols()} FROM jobs WHERE id=%s", (job_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return row_to_jobout(row)


def _assert_participant(cur, job_id: int, user_id: int) -> None:
    cur.execute(
        "SELECT customer_id, provider_id FROM jobs WHERE id=%s",
        (job_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    c, p = row.get("customer_id"), row.get("provider_id")
    if p is None:
        raise HTTPException(status_code=400, detail="chat available after provider is assigned")
    if int(user_id) not in (int(c), int(p)):
        raise HTTPException(status_code=403, detail="not a participant")


def is_job_participant(job_id: int, user_id: int) -> bool:
    try:
        migrate_messages_table()
        with db_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT customer_id, provider_id FROM jobs WHERE id=%s",
                    (job_id,),
                )
                row = cur.fetchone()
        if not row:
            return False
        c, p = row.get("customer_id"), row.get("provider_id")
        if p is None or c is None:
            return False
        return int(user_id) in (int(c), int(p))
    except Exception:
        return False


@router.get("/{job_id}/messages", response_model=List[MessageOut])
async def list_messages(job_id: int, user_id: int = Depends(get_current_user_id)):
    migrate_messages_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _assert_participant(cur, job_id, user_id)
            cur.execute(
                """
                SELECT id, job_id, sender_id, content, created_at
                FROM job_messages WHERE job_id=%s ORDER BY id ASC LIMIT 500
                """,
                (job_id,),
            )
            rows = cur.fetchall()
    return [
        MessageOut(
            id=r["id"],
            job_id=r["job_id"],
            sender_id=r["sender_id"],
            content=r["content"],
            created_at=_ts(r.get("created_at")),
        )
        for r in rows
    ]


@router.post("/{job_id}/messages", response_model=MessageOut, status_code=201)
async def post_message(
    job_id: int, body: MessageIn, user_id: int = Depends(get_current_user_id)
):
    migrate_messages_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            _assert_participant(cur, job_id, user_id)
            cur.execute(
                """
                INSERT INTO job_messages (job_id, sender_id, content)
                VALUES (%s, %s, %s)
                RETURNING id, job_id, sender_id, content, created_at
                """,
                (job_id, user_id, body.content.strip()),
            )
            row = cur.fetchone()
            conn.commit()
    out = MessageOut(
        id=row["id"],
        job_id=row["job_id"],
        sender_id=row["sender_id"],
        content=row["content"],
        created_at=_ts(row.get("created_at")),
    )
    await broadcast_chat(
        job_id,
        {
            "type": "new_message",
            "message": {
                "id": out.id,
                "job_id": out.job_id,
                "sender_id": out.sender_id,
                "content": out.content,
                "created_at": out.created_at,
            },
        },
    )
    return out


def _jobs_near_fallback(lat: float, lon: float, radius_m: int) -> List[JobOut]:
    """Если PostGIS недоступен — грубый bbox + Haversine."""
    import math

    deg_lat = radius_m / 111_320
    deg_lon = radius_m / (40075_000 * math.cos(math.radians(lat)) / 360.0 + 1e-9)
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT {_select_cols()}
                FROM jobs
                WHERE lat BETWEEN %s AND %s
                  AND lon BETWEEN %s AND %s
                  AND status = 'open'
                ORDER BY id DESC
                """,
                (lat - deg_lat, lat + deg_lat, lon - deg_lon, lon + deg_lon),
            )
            rows = cur.fetchall()

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
            math.radians(lat2)
        ) * math.sin(dlon / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    out: List[JobOut] = []
    for r in rows:
        d = haversine(lat, lon, float(r["lat"]), float(r["lon"]))
        if d <= radius_m:
            out.append(row_to_jobout(r, distance_m=d))
    out.sort(key=lambda x: x.distance_m or 0)
    return out


def _assign_impl(job_id: int, provider_id: int, customer_id: int) -> JobOut:
    migrate_jobs_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"SELECT {_select_cols()} FROM jobs WHERE id=%s",
                (job_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
            if row["status"] != "open":
                raise HTTPException(status_code=400, detail="job is not open")
            cid = row.get("customer_id")
            if cid is None:
                raise HTTPException(
                    status_code=400, detail="job has no customer; cannot assign"
                )
            if int(cid) != int(customer_id):
                raise HTTPException(status_code=403, detail="only customer can assign")
            if int(provider_id) == int(customer_id):
                raise HTTPException(status_code=400, detail="cannot assign yourself")

            cur.execute(
                f"""
                UPDATE jobs
                   SET provider_id=%s, status='matched'
                 WHERE id=%s
             RETURNING {_select_cols()}
                """,
                (provider_id, job_id),
            )
            updated = cur.fetchone()
            conn.commit()
            return row_to_jobout(updated)


@router.post("/{job_id}/claim", response_model=JobOut)
async def claim_job(job_id: int, user_id: int = Depends(get_current_user_id)):
    """MVP: первый исполнитель забирает открытое задание (без назначения заказчиком)."""
    migrate_jobs_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                UPDATE jobs
                   SET provider_id=%s, status='matched'
                 WHERE id=%s AND status='open'
                   AND customer_id IS NOT NULL
                   AND customer_id <> %s
                RETURNING {_select_cols()}
                """,
                (user_id, job_id, user_id),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return row_to_jobout(row)
            cur.execute("SELECT id, status, customer_id FROM jobs WHERE id=%s", (job_id,))
            ex = cur.fetchone()
            if not ex:
                raise HTTPException(status_code=404, detail="job not found")
            if ex.get("customer_id") == user_id:
                raise HTTPException(status_code=400, detail="cannot claim own job")
            raise HTTPException(status_code=409, detail="job already taken or not open")


@router.post("/{job_id}/assign", response_model=JobOut)
async def assign_job_post(
    job_id: int, body: AssignBody, user_id: int = Depends(get_current_user_id)
):
    return _assign_impl(job_id, body.provider_id, user_id)


@router.patch("/{job_id}/assign", response_model=JobOut)
async def assign_job_patch(
    job_id: int, provider_id: int, user_id: int = Depends(get_current_user_id)
):
    """Обратная совместимость: provider_id в query."""
    return _assign_impl(job_id, provider_id, user_id)


@router.post("/{job_id}/start", response_model=JobOut)
async def start_job(job_id: int, user_id: int = Depends(get_current_user_id)):
    """Исполнитель начинает работу: matched → in_progress."""
    migrate_jobs_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                UPDATE jobs SET status='in_progress', started_at=COALESCE(started_at, NOW())
                WHERE id=%s AND status='matched' AND provider_id=%s
                RETURNING {_select_cols()}
                """,
                (job_id, user_id),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return row_to_jobout(row)
            cur.execute(
                f"SELECT status, provider_id FROM jobs WHERE id=%s", (job_id,)
            )
            ex = cur.fetchone()
            if not ex:
                raise HTTPException(status_code=404, detail="job not found")
            raise HTTPException(status_code=400, detail="cannot start this job")


@router.post("/{job_id}/complete", response_model=JobOut)
async def complete_job(job_id: int, user_id: int = Depends(get_current_user_id)):
    """Исполнитель завершает: in_progress → completed."""
    migrate_jobs_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                UPDATE jobs SET status='completed', completed_at=NOW()
                WHERE id=%s AND status='in_progress' AND provider_id=%s
                RETURNING {_select_cols()}
                """,
                (job_id, user_id),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return row_to_jobout(row)
            cur.execute(
                f"SELECT status, provider_id FROM jobs WHERE id=%s", (job_id,)
            )
            ex = cur.fetchone()
            if not ex:
                raise HTTPException(status_code=404, detail="job not found")
            raise HTTPException(status_code=400, detail="cannot complete this job")


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: int, user_id: int = Depends(get_current_user_id)):
    """Заказчик или исполнитель отменяет (упрощённое MVP)."""
    migrate_jobs_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                UPDATE jobs SET status='cancelled'
                WHERE id=%s
                  AND status NOT IN ('completed','cancelled')
                  AND (
                       (customer_id=%s AND status IN ('open','matched','in_progress'))
                    OR (provider_id=%s AND status IN ('matched','in_progress'))
                  )
                RETURNING {_select_cols()}
                """,
                (job_id, user_id, user_id),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return row_to_jobout(row)
            cur.execute(
                f"SELECT status, customer_id, provider_id FROM jobs WHERE id=%s",
                (job_id,),
            )
            ex = cur.fetchone()
            if not ex:
                raise HTTPException(status_code=404, detail="job not found")
            raise HTTPException(status_code=403, detail="cannot cancel this job")
