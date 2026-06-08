"""Celery: брокер Redis, периодические задачи (beat)."""
import os
from datetime import timedelta

from celery import Celery

REDIS = os.getenv("REDIS_URL", "redis://redis:6379/0")
INTERVAL = float(os.getenv("CELERY_CLEANUP_INTERVAL_SEC", "300"))

celery_app = Celery(
    "ruki",
    broker=REDIS,
    backend=REDIS,
    include=["backend.app.tasks"],
)

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "cleanup-expired-open-jobs": {
        "task": "backend.app.tasks.cleanup_expired_open_jobs",
        "schedule": timedelta(seconds=INTERVAL),
    },
}
