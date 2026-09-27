"""Pytest configuration for IBVAP backend tests."""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

# Set test environment BEFORE importing models to avoid Track/TrackV2 table conflict
os.environ["ENV"] = "test"
os.environ["PYTEST_CURRENT_TEST"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base

from app.db.database import Base, get_db_session
import app.models  # noqa: F401  (registers all tables on Base.metadata)

TEST_ROOT = Path(__file__).resolve().parent
DB_DIR = TEST_ROOT / "test_dbs"
DB_DIR.mkdir(exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_dbs():
    yield
    # Clean up all test databases after session
    for db_file in DB_DIR.glob("test_*.db"):
        try:
            db_file.unlink()
        except PermissionError:
            pass


@pytest.fixture(scope="function")
async def engine():
    """Async engine against an isolated SQLite file.
    
    Each test gets its own unique database file to ensure complete isolation.
    """
    # Create unique database file for this test
    db_file = DB_DIR / f"test_{uuid.uuid4().hex}.db"
    
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file.as_posix()}",
        poolclass=NullPool,  # Disable connection pooling for test isolation
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()
    await asyncio.sleep(0.05)
    # Clean up the database file
    try:
        db_file.unlink()
    except PermissionError:
        pass


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
def app(session_factory):
    """FastAPI app with the test database wired in via dependency override."""
    from app.main import app

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c