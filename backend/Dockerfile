FROM python:3.11-slim
WORKDIR /app
COPY . /app

# ВАЖНО: PyJWT нужен для auth.py (import jwt)
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] \
    psycopg2-binary sqlalchemy \
    passlib[bcrypt] bcrypt \
    argon2-cffi \
    PyJWT \
    python-jose[cryptography] \
    minio pydantic redis celery

ENV PYTHONPATH=/app
CMD ["uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"]

