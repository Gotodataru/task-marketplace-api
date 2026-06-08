import os, datetime as dt
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.hash import argon2

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_ALG = "HS256"
# Длительность access-токена (минуты). По умолчанию ~30 суток.
ACCESS_MIN = int(os.getenv("JWT_ACCESS_MINUTES", str(60 * 24 * 30)))
REFRESH_DAYS = 30

def hash_password(p: str) -> str:
    return argon2.hash(p)

def verify_password(p: str, h: str) -> bool:
    return argon2.verify(p, h)

def create_access_token(sub: str) -> str:
    now = dt.datetime.utcnow()
    payload = {"sub": sub, "type":"access", "iat": now, "exp": now + dt.timedelta(minutes=ACCESS_MIN)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def create_refresh_token(sub: str) -> str:
    now = dt.datetime.utcnow()
    payload = {"sub": sub, "type":"refresh", "iat": now, "exp": now + dt.timedelta(days=REFRESH_DAYS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        return None

bearer = HTTPBearer(auto_error=False)

async def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    data = decode_token(creds.credentials)
    if not data or data.get("type") != "access":
        raise HTTPException(401, "Invalid token")
    return int(data["sub"])
