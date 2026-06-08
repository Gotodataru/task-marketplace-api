from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from ..db import SessionLocal
from ..security import get_current_user_id

router = APIRouter(prefix="/reviews")

@router.post("/")
async def add_review(job_id: int, to_user_id: int, rating: int, comment: str = "",
                     user_id: int = Depends(get_current_user_id)):
    if rating < 1 or rating > 5:
        raise HTTPException(400, "rating 1..5")
    if user_id == to_user_id:
        raise HTTPException(400, "cannot review yourself")
    async with SessionLocal() as s:
        await s.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS rating_avg NUMERIC(3,2) NOT NULL DEFAULT 0.00"
            )
        )
        await s.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS rating_cnt INT NOT NULL DEFAULT 0"
            )
        )
        job = await s.execute(
            text(
                "SELECT status, customer_id, provider_id FROM jobs WHERE id = :j"
            ),
            {"j": job_id},
        )
        jrow = job.fetchone()
        if not jrow:
            raise HTTPException(404, "job not found")
        st, cid, pid = jrow[0], jrow[1], jrow[2]
        if st not in ("completed", "done"):
            raise HTTPException(400, "job must be completed before review")
        if pid is None or cid is None:
            raise HTTPException(400, "invalid job participants")
        a, b = int(cid), int(pid)
        if {user_id, to_user_id} != {a, b}:
            raise HTTPException(403, "review allowed only between customer and provider of this job")

        exists = await s.execute(text("""
          SELECT 1 FROM reviews WHERE job_id=:j AND from_user_id=:f AND to_user_id=:t
        """), {"j": job_id, "f": user_id, "t": to_user_id})
        if exists.fetchone():
            raise HTTPException(400, "Already reviewed")

        await s.execute(text("""
          INSERT INTO reviews(job_id, from_user_id, to_user_id, rating, comment)
          VALUES(:j,:f,:t,:r,:c)
        """), {"j": job_id, "f": user_id, "t": to_user_id, "r": rating, "c": comment})

        await s.execute(text("""
          WITH agg AS (
            SELECT AVG(rating)::numeric(3,2) a, COUNT(*) c
            FROM reviews WHERE to_user_id=:t
          )
          UPDATE users SET rating_avg=(SELECT a FROM agg), rating_cnt=(SELECT c FROM agg)
          WHERE id=:t
        """), {"t": to_user_id})

        await s.commit()
        return {"ok": True}
