"""Фоновые задачи Celery (sync, psycopg2)."""
import logging
import os

import psycopg2

from .celery_app import celery_app

logger = logging.getLogger("tasks")

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app")
DB_USER = os.getenv("DB_USER", "app")
DB_PASS = os.getenv("DB_PASSWORD", "secret")


def _conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )


@celery_app.task(name="backend.app.tasks.cleanup_expired_open_jobs")
def cleanup_expired_open_jobs() -> int:
    """Отмена открытых заданий с истёкшим expires_at."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jobs
                   SET status = 'cancelled'
                 WHERE status = 'open'
                   AND expires_at IS NOT NULL
                   AND expires_at < NOW()
                """
            )
            n = cur.rowcount
            conn.commit()
    logger.info("cleanup_expired_open_jobs: cancelled %s jobs", n)
    return n
