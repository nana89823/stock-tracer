import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy import MetaData

from app.models.base import Base
from app.database import get_db
from app.main import app
from app.auth.security import create_access_token, get_password_hash

# Import models we need (avoid JSONB models like Strategy/Backtest)
from app.models.user import User as _User
from app.models.stock import Stock as _Stock
from app.models.raw_price import RawPrice as _RawPrice
from app.models.watchlist import Watchlist as _Watchlist
from app.models.price_alert import PriceAlert as _PriceAlert
from app.models.notification import Notification as _Notification

# Tables safe for SQLite (no JSONB)
_TEST_TABLES = [
    Base.metadata.tables["users"],
    Base.metadata.tables["stocks"],
    Base.metadata.tables["raw_prices"],
    Base.metadata.tables["watchlists"],
    Base.metadata.tables["price_alerts"],
    Base.metadata.tables["notifications"],
]

# Use aiosqlite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create only SQLite-compatible tables before each test, drop after."""
    test_metadata = MetaData()
    for table in _TEST_TABLES:
        table.to_metadata(test_metadata)

    async with engine.begin() as conn:
        await conn.run_sync(test_metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(test_metadata.drop_all)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def db_session():
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """Provide an async test client with overridden DB dependency."""
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user and return (user, token)."""
    from app.models.user import User

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(data={"sub": user.username})
    return user, token


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Return authorization headers for the test user."""
    _, token = test_user
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession):
    """Create a second test user for permission tests."""
    from app.models.user import User

    user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password=get_password_hash("otherpass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(data={"sub": user.username})
    return user, token


@pytest_asyncio.fixture
async def other_auth_headers(other_user):
    """Return authorization headers for the other user."""
    _, token = other_user
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_stock(db_session: AsyncSession):
    """Create a sample stock."""
    from app.models.stock import Stock

    stock = Stock(stock_id="2330", stock_name="台積電", market_type="twse")
    db_session.add(stock)
    await db_session.commit()
    return stock


@pytest_asyncio.fixture
async def sample_stocks(db_session: AsyncSession):
    """Create multiple sample stocks."""
    from app.models.stock import Stock

    stocks = [
        Stock(stock_id="2330", stock_name="台積電", market_type="twse"),
        Stock(stock_id="2317", stock_name="鴻海", market_type="twse"),
        Stock(stock_id="2454", stock_name="聯發科", market_type="twse"),
    ]
    db_session.add_all(stocks)
    await db_session.commit()
    return stocks


@pytest_asyncio.fixture
async def sample_price(db_session: AsyncSession, sample_stock):
    """Create a sample price record for the stock."""
    from app.models.raw_price import RawPrice

    price = RawPrice(
        date=datetime(2026, 3, 14),
        stock_id="2330",
        stock_name="台積電",
        trade_volume=30000000,
        trade_value=25500000000,
        open_price=845.0,
        high_price=855.0,
        low_price=840.0,
        close_price=850.0,
        price_change=10.0,
        transaction_count=50000,
    )
    db_session.add(price)
    await db_session.commit()
    return price
