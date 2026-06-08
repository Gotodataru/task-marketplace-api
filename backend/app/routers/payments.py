"""Мок платежей (эскроу): hold / release / refund — без реального шлюза."""
import os
import logging
from typing import Optional, Any, Dict

import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from ..security import get_current_user_id

logger = logging.getLogger("payments")
router = APIRouter()

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "app")
DB_PASS = os.getenv("DB_PASSWORD", "secret")


def db_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )


def ensure_payments_table() -> None:
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payment_transactions (
                        id SERIAL PRIMARY KEY,
                        job_id INTEGER NOT NULL,
                        customer_id INTEGER NOT NULL,
                        provider_id INTEGER,
                        amount_rub INTEGER NOT NULL,
                        commission_rub INTEGER NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'held',
                        external_id TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS ix_payment_transactions_job_id ON payment_transactions(job_id)"
                )
            conn.commit()
    except Exception as e:
        logger.warning("ensure_payments_table: %s", e)


class HoldBody(BaseModel):
    job_id: int = Field(..., ge=1)
    amount_rub: Optional[int] = Field(None, ge=0)


class TxOut(BaseModel):
    id: int
    job_id: int
    status: str
    amount_rub: int
    commission_rub: int


def _row_to_out(row: Dict[str, Any]) -> TxOut:
    return TxOut(
        id=row["id"],
        job_id=row["job_id"],
        status=row["status"],
        amount_rub=row["amount_rub"],
        commission_rub=row["commission_rub"],
    )


@router.post("/hold", response_model=TxOut)
async def hold(body: HoldBody, user_id: int = Depends(get_current_user_id)):
    """Имитация блокирования средств по заданию (заказчик)."""
    ensure_payments_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, price_rub, customer_id, provider_id, status
                FROM jobs WHERE id=%s
                """,
                (body.job_id,),
            )
            job = cur.fetchone()
            if not job:
                raise HTTPException(404, "job not found")
            if int(job["customer_id"] or 0) != int(user_id):
                raise HTTPException(403, "only customer")
            if job["status"] not in ("matched", "in_progress"):
                raise HTTPException(400, "job must be matched or in progress")
            amt = body.amount_rub if body.amount_rub is not None else int(job["price_rub"])
            comm = max(0, int(amt * 0.1))
            cur.execute(
                """
                INSERT INTO payment_transactions
                  (job_id, customer_id, provider_id, amount_rub, commission_rub, status)
                VALUES (%s, %s, %s, %s, %s, 'held')
                RETURNING id, job_id, status, amount_rub, commission_rub
                """,
                (
                    body.job_id,
                    job["customer_id"],
                    job["provider_id"],
                    amt,
                    comm,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return _row_to_out(row)


class JobIdBody(BaseModel):
    job_id: int = Field(..., ge=1)


@router.post("/release", response_model=TxOut)
async def release(body: JobIdBody, user_id: int = Depends(get_current_user_id)):
    """Имитация перевода исполнителю после выполнения."""
    ensure_payments_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT customer_id, status FROM jobs WHERE id=%s",
                (body.job_id,),
            )
            job = cur.fetchone()
            if not job:
                raise HTTPException(404, "job not found")
            if int(job["customer_id"] or 0) != int(user_id):
                raise HTTPException(403, "only customer")
            if job["status"] != "completed":
                raise HTTPException(400, "job must be completed")
            cur.execute(
                """
                UPDATE payment_transactions
                   SET status='released', updated_at=NOW()
                 WHERE job_id=%s AND status='held'
                 RETURNING id, job_id, status, amount_rub, commission_rub
                """,
                (body.job_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "no held transaction for this job")
            conn.commit()
            return _row_to_out(row)


@router.post("/refund", response_model=TxOut)
async def refund(body: JobIdBody, user_id: int = Depends(get_current_user_id)):
    """Имитация возврата при отмене."""
    ensure_payments_table()
    with db_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT customer_id FROM jobs WHERE id=%s",
                (body.job_id,),
            )
            job = cur.fetchone()
            if not job:
                raise HTTPException(404, "job not found")
            if int(job["customer_id"] or 0) != int(user_id):
                raise HTTPException(403, "only customer")
            cur.execute(
                """
                UPDATE payment_transactions
                   SET status='refunded', updated_at=NOW()
                 WHERE job_id=%s AND status='held'
                 RETURNING id, job_id, status, amount_rub, commission_rub
                """,
                (body.job_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "no held transaction to refund")
            conn.commit()
            return _row_to_out(row)
