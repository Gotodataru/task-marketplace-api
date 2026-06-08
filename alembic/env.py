import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

config = context.config
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass


def get_url() -> str:
    u = os.getenv("DATABASE_URL")
    if u:
        return (
            u.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            .replace("+asyncpg", "+psycopg2")
        )
    user = os.getenv("DB_USER", "app")
    password = os.getenv("DB_PASSWORD", "secret")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "app")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
