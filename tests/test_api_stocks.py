"""Integration tests for Stock API endpoints (/api/v1/stocks/...)."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import get_current_user
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.broker_trading import BrokerTrading
from app.models.major_holders import MajorHolders
from app.models.margin_trading import MarginTrading
from app.models.raw_chip import RawChip
from app.models.raw_price import RawPrice
from app.models.stock import Stock
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
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


async def _override_get_db():
    async with _TestSessionLocal() as session:
        yield session


# Fake user for auth override
_fake_user = User(
    id=1,
    username="testuser",
    email="test@example.com",
    hashed_password="fakehash",
    is_active=True,
)


async def _override_get_current_user():
    return _fake_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Tables needed for stock API tests (exclude Strategy/Backtest which use JSONB)
_test_tables = [
    User.__table__,
    Stock.__table__,
    RawPrice.__table__,
    RawChip.__table__,
    MajorHolders.__table__,
    MarginTrading.__table__,
    BrokerTrading.__table__,
]


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create needed tables before each test and drop after."""
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    async with _test_engine.begin() as conn:
        for table in _test_tables:
            await conn.run_sync(table.create, checkfirst=True)
    yield
    async with _test_engine.begin() as conn:
        for table in reversed(_test_tables):
            await conn.run_sync(table.drop, checkfirst=True)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def seeded_db():
    """Seed sample stock data and return the session."""
    async with _TestSessionLocal() as session:
        # Stocks
        session.add_all([
            Stock(stock_id="2330", stock_name="台積電", market_type="twse"),
            Stock(stock_id="2317", stock_name="鴻海", market_type="twse"),
            Stock(stock_id="0050", stock_name="元大台灣50", market_type="twse"),
        ])
        await session.flush()

        # Raw prices
        session.add_all([
            RawPrice(
                date=date(2026, 1, 20), stock_id="2330", stock_name="台積電",
                trade_volume=25000000, trade_value=25000000000,
                open_price=1000, high_price=1010, low_price=995,
                close_price=1005, price_change=5, transaction_count=100000,
            ),
            RawPrice(
                date=date(2026, 1, 21), stock_id="2330", stock_name="台積電",
                trade_volume=20000000, trade_value=20000000000,
                open_price=1005, high_price=1015, low_price=1000,
                close_price=1010, price_change=5, transaction_count=90000,
            ),
        ])

        # Raw chips
        session.add_all([
            RawChip(
                date=date(2026, 1, 20), stock_id="2330", stock_name="台積電",
                foreign_buy=5000000, foreign_sell=3000000, foreign_net=2000000,
                foreign_dealer_buy=100000, foreign_dealer_sell=50000, foreign_dealer_net=50000,
                trust_buy=500000, trust_sell=200000, trust_net=300000,
                dealer_net=150000, dealer_self_buy=100000, dealer_self_sell=50000,
                dealer_self_net=50000, dealer_hedge_buy=200000, dealer_hedge_sell=100000,
                dealer_hedge_net=100000, total_net=2500000,
            ),
        ])

        # Major holders
        session.add_all([
            MajorHolders(
                date=date(2026, 1, 23), stock_id="2330",
                holding_level=1, holder_count=500000, share_count=100000000,
                holding_ratio=0.38,
            ),
            MajorHolders(
                date=date(2026, 1, 23), stock_id="2330",
                holding_level=2, holder_count=300000, share_count=500000000,
                holding_ratio=1.92,
            ),
        ])

        # Margin trading
        session.add_all([
            MarginTrading(
                date=date(2026, 1, 20), stock_id="2330",
                margin_buy=1000, margin_sell=500, margin_cash_repay=100,
                margin_balance_prev=10000, margin_balance=10400,
                margin_limit=50000,
                short_buy=200, short_sell=300, short_cash_repay=50,
                short_balance_prev=5000, short_balance=5050,
                short_limit=20000, offset=0, note="",
            ),
        ])

        # Broker trading
        session.add_all([
            BrokerTrading(
                date=date(2026, 1, 20), stock_id="2330",
                broker_id="1234", broker_name="元大證券",
                price=1005.0, buy_volume=500000, sell_volume=300000,
            ),
            BrokerTrading(
                date=date(2026, 1, 20), stock_id="2330",
                broker_id="5678", broker_name="凱基證券",
                price=1005.0, buy_volume=200000, sell_volume=400000,
            ),
        ])

        await session.commit()


# ---------------------------------------------------------------------------
# Patch cache so it always misses (no Redis needed)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _no_cache():
    with patch("app.api.stocks.get_cache", new_callable=AsyncMock, return_value=None), \
         patch("app.api.stocks.set_cache", new_callable=AsyncMock):
        yield


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ===========================================================================
# 1. Unauthenticated access
# ===========================================================================

@pytest.mark.asyncio
async def test_unauthenticated_access_returns_401():
    """All stock endpoints should return 401 without a valid token."""
    # Temporarily remove the auth override so the real dependency kicks in
    saved = app.dependency_overrides.pop(get_current_user, None)
    try:
        async with _client() as client:
            resp = await client.get("/api/v1/stocks/")
            assert resp.status_code == 401

            resp = await client.get("/api/v1/stocks/2330")
            assert resp.status_code == 401

            resp = await client.get("/api/v1/stocks/2330/prices")
            assert resp.status_code == 401

            resp = await client.get("/api/v1/stocks/2330/chips")
            assert resp.status_code == 401

            resp = await client.get("/api/v1/stocks/2330/holders")
            assert resp.status_code == 401

            resp = await client.get("/api/v1/stocks/2330/margin")
            assert resp.status_code == 401

            resp = await client.get("/api/v1/stocks/2330/brokers")
            assert resp.status_code == 401
    finally:
        if saved is not None:
            app.dependency_overrides[get_current_user] = saved


# ===========================================================================
# 2. Search stocks (GET /api/v1/stocks/)
# ===========================================================================

@pytest.mark.asyncio
async def test_search_stocks(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/", params={"q": "台積"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["stock_id"] == "2330"
    assert data[0]["stock_name"] == "台積電"
    assert "X-Total-Count" in resp.headers


@pytest.mark.asyncio
async def test_search_stocks_by_id(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/", params={"q": "2330"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["stock_id"] == "2330"


@pytest.mark.asyncio
async def test_search_stocks_empty_result(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/", params={"q": "不存在的股票"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0
    assert resp.headers["X-Total-Count"] == "0"


@pytest.mark.asyncio
async def test_search_stocks_no_query_returns_all(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_search_stocks_pagination(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/", params={"skip": 0, "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert resp.headers["X-Total-Count"] == "3"


@pytest.mark.asyncio
async def test_search_stocks_pagination_skip(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/", params={"skip": 2, "limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


# ===========================================================================
# 3. Stock detail (GET /api/v1/stocks/{stock_id})
# ===========================================================================

@pytest.mark.asyncio
async def test_get_stock_found(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/2330")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stock_id"] == "2330"
    assert data["stock_name"] == "台積電"
    assert data["market_type"] == "twse"


@pytest.mark.asyncio
async def test_get_stock_not_found(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Stock not found"


# ===========================================================================
# 4. Prices (GET /api/v1/stocks/{stock_id}/prices)
# ===========================================================================

@pytest.mark.asyncio
async def test_get_prices(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/2330/prices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["stock_id"] == "2330"
    assert data[0]["close_price"] == 1005


@pytest.mark.asyncio
async def test_get_prices_with_date_range(seeded_db):
    async with _client() as client:
        resp = await client.get(
            "/api/v1/stocks/2330/prices",
            params={"start_date": "2026-01-21", "end_date": "2026-01-21"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["close_price"] == 1010


@pytest.mark.asyncio
async def test_get_prices_empty(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/9999/prices")
    assert resp.status_code == 200
    assert resp.json() == []


# ===========================================================================
# 5. Chips (GET /api/v1/stocks/{stock_id}/chips)
# ===========================================================================

@pytest.mark.asyncio
async def test_get_chips(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/2330/chips")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["foreign_net"] == 2000000
    assert data[0]["total_net"] == 2500000


@pytest.mark.asyncio
async def test_get_chips_with_date_range(seeded_db):
    async with _client() as client:
        resp = await client.get(
            "/api/v1/stocks/2330/chips",
            params={"start_date": "2026-01-21"},
        )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_chips_empty(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/9999/chips")
    assert resp.status_code == 200
    assert resp.json() == []


# ===========================================================================
# 6. Major holders (GET /api/v1/stocks/{stock_id}/holders)
# ===========================================================================

@pytest.mark.asyncio
async def test_get_holders(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/2330/holders")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["holding_level"] == 1
    assert data[1]["holding_level"] == 2


@pytest.mark.asyncio
async def test_get_holders_with_date(seeded_db):
    async with _client() as client:
        resp = await client.get(
            "/api/v1/stocks/2330/holders",
            params={"date_param": "2026-01-23"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_holders_wrong_date(seeded_db):
    async with _client() as client:
        resp = await client.get(
            "/api/v1/stocks/2330/holders",
            params={"date_param": "2026-01-01"},
        )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_holders_empty(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/9999/holders")
    assert resp.status_code == 200
    assert resp.json() == []


# ===========================================================================
# 7. Margin trading (GET /api/v1/stocks/{stock_id}/margin)
# ===========================================================================

@pytest.mark.asyncio
async def test_get_margin(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/2330/margin")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["margin_buy"] == 1000
    assert data[0]["margin_balance"] == 10400
    assert data[0]["short_balance"] == 5050


@pytest.mark.asyncio
async def test_get_margin_with_date_range(seeded_db):
    async with _client() as client:
        resp = await client.get(
            "/api/v1/stocks/2330/margin",
            params={"start_date": "2026-01-20", "end_date": "2026-01-20"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_get_margin_empty(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/9999/margin")
    assert resp.status_code == 200
    assert resp.json() == []


# ===========================================================================
# 8. Broker trading (GET /api/v1/stocks/{stock_id}/brokers)
# ===========================================================================

@pytest.mark.asyncio
async def test_get_brokers(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/2330/brokers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_brokers_filter_by_broker_id(seeded_db):
    async with _client() as client:
        resp = await client.get(
            "/api/v1/stocks/2330/brokers",
            params={"broker_id": "1234"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["broker_name"] == "元大證券"
    assert data[0]["buy_volume"] == 500000


@pytest.mark.asyncio
async def test_get_brokers_with_date_range(seeded_db):
    async with _client() as client:
        resp = await client.get(
            "/api/v1/stocks/2330/brokers",
            params={"start_date": "2026-01-20", "end_date": "2026-01-20"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_brokers_empty(seeded_db):
    async with _client() as client:
        resp = await client.get("/api/v1/stocks/9999/brokers")
    assert resp.status_code == 200
    assert resp.json() == []
