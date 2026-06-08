# media.py — clean version

import os
import uuid
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from minio import Minio
from sqlalchemy import text
from ..db import SessionLocal
from ..security import get_current_user_id

router = APIRouter()

# ── Конфиг из .env ────────────────────────────────────────────────────────────
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "media")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")

# ── MinIO client ───────────────────────────────────────────────────────────────
_mc = None

def get_mc() -> Minio:
    global _mc
    if _mc is None:
        parsed = urlparse(MINIO_ENDPOINT)
        secure = parsed.scheme == "https"
        endpoint = parsed.netloc
        _mc = Minio(
            endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=secure,
        )
    return _mc

def ensure_bucket() -> None:
    mc = get_mc()
    if not mc.bucket_exists(MINIO_BUCKET):
        mc.make_bucket(MINIO_BUCKET)

# ── Эндпоинты ─────────────────────────────────────────────────────────────────
@router.post("/presign-upload")
async def presign_upload(user_id: int = Depends(get_current_user_id)):
    """
    Генерирует безопасное имя файла и возвращает presigned URL для загрузки.
    """
    ensure_bucket()
    mc = get_mc()
    object_name = f"{user_id}/{uuid.uuid4().hex}.jpg"  # или .png — клиент сам выберет тип
    try:
        upload_url = mc.presigned_put_object(MINIO_BUCKET, object_name, expires=600)  # 10 мин
        return {
            "upload_url": upload_url,
            "object_name": object_name,
        }
    except Exception as e:
        raise HTTPException(500, f"MinIO error: {e}")

@router.post("/attach")
async def attach_media(
    session_id: int,
    object_name: str,
    kind: str = "photo",
    user_id: int = Depends(get_current_user_id),
):
    """
    Привязывает object_name к сессии. URL не сохраняется — он генерится при запросе отчёта.
    """
    async with SessionLocal() as s:
        await s.execute(
            text("""
                INSERT INTO media(session_id, uploader_id, object_name, kind)
                VALUES(:sid, :uid, :obj, :kind)
            """),
            {"sid": session_id, "uid": user_id, "obj": object_name, "kind": kind},
        )
        await s.commit()
        return {"ok": True}