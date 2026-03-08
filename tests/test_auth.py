"""Tests for auth register and login endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models.user import User

# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests
# ---------------------------------------------------------------------------
_test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)


@event.listens_for(_test_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    """Enable WAL mode for SQLite (optional, helps concurrency)."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


async def _override_get_db():
    async with _TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create all tables before each test and drop after."""
    app.dependency_overrides[get_db] = _override_get_db
    async with _test_engine.begin() as conn:
        await conn.run_sync(User.__table__.create, checkfirst=True)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(User.__table__.drop, checkfirst=True)
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helper: mock rate limiter so it never blocks
# ---------------------------------------------------------------------------
def _no_rate_limit():
    """Patch login_rate_limit to be a no-op."""
    async def _noop(*_args, **_kwargs):
        return None
    return patch("app.auth.router.login_rate_limit", _noop)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "Secret123"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "bob", "email": "bob@example.com", "password": "Secret123"},
        )
        resp = await client.post(
            "/api/v1/auth/register",
            json={"username": "bob", "email": "bob@example.com", "password": "Secret123"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "carol", "email": "carol@example.com", "password": "Secret123"},
        )
        with _no_rate_limit():
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "carol", "password": "Secret123"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "dave", "email": "dave@example.com", "password": "Secret123"},
        )
        with _no_rate_limit():
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "dave", "password": "WrongPassword"},
            )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limit():
    """Verify that the rate limiter returns 429 when Redis reports too many attempts."""
    # Mock Redis to simulate exceeding the rate limit
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=999)  # way over limit
    mock_redis.expire = AsyncMock()
    mock_redis.ttl = AsyncMock(return_value=45)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a user first
        await client.post(
            "/api/v1/auth/register",
            json={"username": "eve", "email": "eve@example.com", "password": "Secret123"},
        )

        # Patch _get_redis to return our mock
        with patch("app.auth.rate_limit._get_redis", return_value=mock_redis):
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "eve", "password": "Secret123"},
            )

    assert resp.status_code == 429
    assert "Too many login attempts" in resp.json()["detail"]
