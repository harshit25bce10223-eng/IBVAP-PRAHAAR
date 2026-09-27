# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Database Engine & Session Management
# ─────────────────────────────────────────────────────────────────────────────
# SQLAlchemy 2.x async engine over aiosqlite (SQLite) for local development.
# The declarative base + explicit models keep the schema portable so the
# migration to PostgreSQL later is a configuration change, not a rewrite.
# ─────────────────────────────────────────────────────────────────────────────
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
)

# Explicit pool settings only matter for PostgreSQL; SQLite ignores them.
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing a request-scoped async session."""
    async with SessionLocal() as session:
        yield session
