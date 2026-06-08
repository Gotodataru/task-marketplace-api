"""WebSocket-комнаты по job_id; опционально Redis pub/sub между воркерами."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger("realtime")

REDIS_URL = os.getenv("REDIS_URL", "").strip()


class JobChatHub:
    def __init__(self) -> None:
        self._rooms: Dict[int, Set[WebSocket]] = {}

    async def connect(self, job_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms.setdefault(job_id, set()).add(ws)

    def disconnect(self, job_id: int, ws: WebSocket) -> None:
        self._rooms.get(job_id, set()).discard(ws)

    async def broadcast_local(self, job_id: int, payload: dict) -> None:
        room = self._rooms.get(job_id)
        if not room:
            return
        dead: list[WebSocket] = []
        for ws in list(room):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            room.discard(ws)


job_chat_hub = JobChatHub()

_redis = None


async def _redis():
    global _redis
    if _redis is None and REDIS_URL:
        import redis.asyncio as redis

        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def broadcast_chat(job_id: int, payload: dict) -> None:
    """Если задан REDIS_URL — только publish (раздаёт listener); иначе локально."""
    if not REDIS_URL:
        await job_chat_hub.broadcast_local(job_id, payload)
        return
    r = await _redis()
    if not r:
        await job_chat_hub.broadcast_local(job_id, payload)
        return
    await r.publish(
        "job_chat_fanout",
        json.dumps({"job_id": job_id, "payload": payload}),
    )


async def start_redis_listener() -> None:
    """Фон: подписка на канал, доставка в локальные WS (все воркеры)."""
    if not REDIS_URL:
        return
    import redis.asyncio as redis

    r = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("job_chat_fanout")
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not msg or msg.get("type") != "message":
                continue
            try:
                data = json.loads(msg["data"])
                await job_chat_hub.broadcast_local(
                    int(data["job_id"]), data["payload"]
                )
            except Exception as e:
                logger.debug("redis fanout parse: %s", e)
    except asyncio.CancelledError:
        raise
    finally:
        try:
            await pubsub.unsubscribe("job_chat_fanout")
            await r.close()
        except Exception:
            pass
