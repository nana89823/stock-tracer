import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAlertsCRUD:
    """Test alert CRUD operations."""

    async def test_list_empty(self, client: AsyncClient, auth_headers, test_user):
        res = await client.get("/api/v1/alerts/", headers=auth_headers)
        assert res.status_code == 200
        assert res.json() == []

    async def test_create_alert_above(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        assert res.status_code == 201
        data = res.json()
        assert data["stock_id"] == "2330"
        assert data["condition_type"] == "above"
        assert data["threshold"] == 900.0
        assert data["is_active"] is True
        assert data["is_triggered"] is False
        assert data["stock_name"] == "台積電"

    async def test_create_alert_below(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "below", "threshold": 800.0
        })
        assert res.status_code == 201
        assert res.json()["condition_type"] == "below"

    async def test_create_alert_invalid_stock(self, client: AsyncClient, auth_headers, test_user):
        res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "9999", "condition_type": "above", "threshold": 100.0
        })
        assert res.status_code == 404

    async def test_create_alert_invalid_threshold(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": -10.0
        })
        assert res.status_code == 422  # Pydantic validation error

    async def test_create_alert_invalid_condition(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "invalid", "threshold": 100.0
        })
        assert res.status_code == 422

    async def test_list_alerts(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "below", "threshold": 800.0
        })
        res = await client.get("/api/v1/alerts/", headers=auth_headers)
        assert len(res.json()) == 2

    async def test_update_alert_threshold(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        create_res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        alert_id = create_res.json()["id"]

        res = await client.patch(f"/api/v1/alerts/{alert_id}", headers=auth_headers, json={
            "threshold": 950.0
        })
        assert res.status_code == 200
        assert res.json()["threshold"] == 950.0

    async def test_update_alert_deactivate(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        create_res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        alert_id = create_res.json()["id"]

        res = await client.patch(f"/api/v1/alerts/{alert_id}", headers=auth_headers, json={
            "is_active": False
        })
        assert res.json()["is_active"] is False

    async def test_update_reactivate_resets_triggered(self, client: AsyncClient, auth_headers, test_user, sample_stock, db_session):
        """Re-enabling an alert should reset is_triggered."""
        from app.models.price_alert import PriceAlert

        create_res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        alert_id = create_res.json()["id"]

        # Manually mark as triggered
        from sqlalchemy import update
        await db_session.execute(
            update(PriceAlert).where(PriceAlert.id == alert_id).values(is_triggered=True)
        )
        await db_session.commit()

        # Re-activate should reset triggered
        res = await client.patch(f"/api/v1/alerts/{alert_id}", headers=auth_headers, json={
            "is_active": True
        })
        assert res.json()["is_triggered"] is False

    async def test_delete_alert(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        create_res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        alert_id = create_res.json()["id"]

        res = await client.delete(f"/api/v1/alerts/{alert_id}", headers=auth_headers)
        assert res.status_code == 204

        # Verify deleted
        res = await client.get("/api/v1/alerts/", headers=auth_headers)
        assert len(res.json()) == 0

    async def test_delete_nonexistent(self, client: AsyncClient, auth_headers, test_user):
        res = await client.delete("/api/v1/alerts/99999", headers=auth_headers)
        assert res.status_code == 404


@pytest.mark.asyncio
class TestAlertsAuth:
    """Test alerts authentication and authorization."""

    async def test_no_auth(self, client: AsyncClient):
        assert (await client.get("/api/v1/alerts/")).status_code == 401
        assert (await client.post("/api/v1/alerts/", json={"stock_id": "2330", "condition_type": "above", "threshold": 100})).status_code == 401

    async def test_cross_user_update(self, client: AsyncClient, auth_headers, other_auth_headers, test_user, other_user, sample_stock):
        create_res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        alert_id = create_res.json()["id"]

        # Other user cannot update
        res = await client.patch(f"/api/v1/alerts/{alert_id}", headers=other_auth_headers, json={"threshold": 950.0})
        assert res.status_code == 404

    async def test_cross_user_delete(self, client: AsyncClient, auth_headers, other_auth_headers, test_user, other_user, sample_stock):
        create_res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        alert_id = create_res.json()["id"]

        res = await client.delete(f"/api/v1/alerts/{alert_id}", headers=other_auth_headers)
        assert res.status_code == 404

    async def test_cross_user_list_isolation(self, client: AsyncClient, auth_headers, other_auth_headers, test_user, other_user, sample_stock):
        await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 900.0
        })
        res = await client.get("/api/v1/alerts/", headers=other_auth_headers)
        assert res.json() == []


@pytest.mark.asyncio
class TestAlertsLimit:
    """Test alert count limit."""

    async def test_20_alert_limit(self, client: AsyncClient, auth_headers, test_user, sample_stock):
        for i in range(20):
            res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
                "stock_id": "2330", "condition_type": "above", "threshold": 800.0 + i
            })
            assert res.status_code == 201

        # 21st should fail
        res = await client.post("/api/v1/alerts/", headers=auth_headers, json={
            "stock_id": "2330", "condition_type": "above", "threshold": 999.0
        })
        assert res.status_code == 400
        assert "20" in res.json()["detail"]
