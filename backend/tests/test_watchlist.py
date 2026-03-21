import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestWatchlistCRUD:
    """Test basic watchlist CRUD operations."""

    async def test_list_empty(self, client: AsyncClient, auth_headers, test_user):
        """Empty watchlist returns empty list."""
        res = await client.get("/api/v1/watchlist/", headers=auth_headers)
        assert res.status_code == 200
        assert res.json() == []

    async def test_add_stock(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        """Successfully add a stock to watchlist."""
        res = await client.post(
            "/api/v1/watchlist/",
            headers=auth_headers,
            json={"stock_id": "2330"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["stock_id"] == "2330"
        assert data["stock_name"] == "台積電"

    async def test_add_nonexistent_stock(self, client: AsyncClient, auth_headers, test_user):
        """Adding a non-existent stock returns 404."""
        res = await client.post(
            "/api/v1/watchlist/",
            headers=auth_headers,
            json={"stock_id": "9999"},
        )
        assert res.status_code == 404

    async def test_add_duplicate(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        """Adding the same stock twice returns 409."""
        await client.post("/api/v1/watchlist/", headers=auth_headers, json={"stock_id": "2330"})
        res = await client.post("/api/v1/watchlist/", headers=auth_headers, json={"stock_id": "2330"})
        assert res.status_code == 409

    async def test_list_with_items(self, client: AsyncClient, auth_headers, test_user, sample_stock, sample_price):
        """List should include stock info and latest price."""
        await client.post("/api/v1/watchlist/", headers=auth_headers, json={"stock_id": "2330"})
        res = await client.get("/api/v1/watchlist/", headers=auth_headers)
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["stock_id"] == "2330"
        assert items[0]["stock_name"] == "台積電"
        assert items[0]["close_price"] == 850.0

    async def test_check_watched(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        """Check endpoint returns correct watched status."""
        # Before adding
        res = await client.get("/api/v1/watchlist/check/2330", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["is_watched"] is False

        # After adding
        await client.post("/api/v1/watchlist/", headers=auth_headers, json={"stock_id": "2330"})
        res = await client.get("/api/v1/watchlist/check/2330", headers=auth_headers)
        assert res.json()["is_watched"] is True

    async def test_remove_stock(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        """Successfully remove a stock from watchlist."""
        await client.post("/api/v1/watchlist/", headers=auth_headers, json={"stock_id": "2330"})
        res = await client.delete("/api/v1/watchlist/2330", headers=auth_headers)
        assert res.status_code == 204

        # Verify removed
        res = await client.get("/api/v1/watchlist/check/2330", headers=auth_headers)
        assert res.json()["is_watched"] is False

    async def test_remove_nonexistent(self, client: AsyncClient, auth_headers, test_user):
        """Removing a stock not in watchlist returns 404."""
        res = await client.delete("/api/v1/watchlist/9999", headers=auth_headers)
        assert res.status_code == 404


@pytest.mark.asyncio
class TestWatchlistAuth:
    """Test watchlist authentication and authorization."""

    async def test_no_auth_returns_401(self, client: AsyncClient):
        """All endpoints require authentication."""
        assert (await client.get("/api/v1/watchlist/")).status_code == 401
        assert (await client.post("/api/v1/watchlist/", json={"stock_id": "2330"})).status_code == 401
        assert (await client.delete("/api/v1/watchlist/2330")).status_code == 401
        assert (await client.get("/api/v1/watchlist/check/2330")).status_code == 401

    async def test_cross_user_isolation(
        self, client: AsyncClient, auth_headers, other_auth_headers,
        test_user, other_user, sample_stock,
    ):
        """Users cannot see or delete each other's watchlist items."""
        # User 1 adds stock
        await client.post("/api/v1/watchlist/", headers=auth_headers, json={"stock_id": "2330"})

        # User 2 cannot see it
        res = await client.get("/api/v1/watchlist/", headers=other_auth_headers)
        assert res.json() == []

        # User 2 cannot delete it
        res = await client.delete("/api/v1/watchlist/2330", headers=other_auth_headers)
        assert res.status_code == 404

    async def test_cross_user_check(
        self, client: AsyncClient, auth_headers, other_auth_headers,
        test_user, other_user, sample_stock,
    ):
        """Check endpoint is user-scoped."""
        await client.post("/api/v1/watchlist/", headers=auth_headers, json={"stock_id": "2330"})

        res = await client.get("/api/v1/watchlist/check/2330", headers=other_auth_headers)
        assert res.json()["is_watched"] is False


@pytest.mark.asyncio
class TestWatchlistLimit:
    """Test watchlist item limit."""

    async def test_50_item_limit(self, client: AsyncClient, auth_headers, test_user, db_session):
        """Cannot add more than 50 items."""
        from app.models.stock import Stock

        # Create 51 stocks
        stocks = [Stock(stock_id=f"S{i:04d}", stock_name=f"Stock{i}", market_type="twse") for i in range(51)]
        db_session.add_all(stocks)
        await db_session.commit()

        # Add 50 items (should all succeed)
        for i in range(50):
            res = await client.post(
                "/api/v1/watchlist/", headers=auth_headers,
                json={"stock_id": f"S{i:04d}"},
            )
            assert res.status_code == 201, f"Failed at item {i}: {res.json()}"

        # 51st should fail
        res = await client.post(
            "/api/v1/watchlist/", headers=auth_headers,
            json={"stock_id": "S0050"},
        )
        assert res.status_code == 400
        assert "50" in res.json()["detail"]
