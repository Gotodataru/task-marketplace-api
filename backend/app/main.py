# backend/app/main.py
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    try:
        from .realtime import REDIS_URL, start_redis_listener

        if REDIS_URL:
            task = asyncio.create_task(start_redis_listener())
    except Exception as e:
        print("Redis listener:", e)
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Ruki — локальные поручения",
    description="Задания рядом: гео-поиск, отзывы, исполнители (MVP API).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
async def healthz():
    return {"ok": True}

# walks — legacy (выгул), отключён; см. ТЗ
try:
    from .routers import auth, jobs, media, reviews, payments
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
    app.include_router(media.router, prefix="/media", tags=["media"])
    app.include_router(reviews.router, tags=["reviews"])
    app.include_router(payments.router, prefix="/payments", tags=["payments"])
except Exception as e:
    print("Failed to load routers:", e)

try:
    from .security import decode_token
    from .realtime import job_chat_hub
    from .routers.jobs import is_job_participant

    @app.websocket("/ws/jobs/{job_id}")
    async def ws_job_chat(
        websocket: WebSocket,
        job_id: int,
        token: str = Query(""),
    ):
        data = decode_token(token) if token else None
        if not data or data.get("type") != "access":
            await websocket.close(code=1008)
            return
        try:
            uid = int(data["sub"])
        except (KeyError, TypeError, ValueError):
            await websocket.close(code=1008)
            return
        if not is_job_participant(job_id, uid):
            await websocket.close(code=1008)
            return
        await job_chat_hub.connect(job_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            job_chat_hub.disconnect(job_id, websocket)
except Exception as e:
    print("WebSocket chat not loaded:", e)