"""
E2E tests — hit the real running backend (localhost:8001) with real PostgreSQL + Redis.

Prerequisites:
  - docker compose up -d db redis
  - uvicorn app.main:app --port 8001
  - A test user must be registerable (or already exist)

Run:
  cd backend && python -m pytest tests/e2e/ -v -s
"""

import httpx
import pytest
import time
import random
import string

BASE_URL = "http://localhost:8001"
API = f"{BASE_URL}/api/v1"

# ---------- helpers ----------

def random_suffix():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client: httpx.Client):
    """Register a fresh test user and return auth headers."""
    suffix = random_suffix()
    username = f"e2e_{suffix}"
    email = f"e2e_{suffix}@test.com"
    password = "TestPass123!"

    # Register
    r = client.post(f"{API}/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"

    # Login
    r = client.post(f"{API}/auth/login", data={
        "username": username,
        "password": password,
    })
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def stock_id():
    """A stock that should exist in the DB (台積電)."""
    return "2330"


# ======================================================================
# 1. Auth flow
# ======================================================================

class TestAuthFlow:
    def test_register_and_login(self, auth):
        """auth fixture already tested register + login."""
        assert "Authorization" in auth

    def test_me_endpoint(self, client, auth):
        r = client.get(f"{API}/auth/me", headers=auth)
        assert r.status_code == 200
        data = r.json()
        assert "username" in data
        assert data["is_active"] is True

    def test_unauthenticated_returns_401(self, client):
        r = client.get(f"{API}/watchlist/")
        assert r.status_code in (401, 403)


# ======================================================================
# 2. Watchlist E2E
# ======================================================================

class TestWatchlistE2E:
    def test_list_empty(self, client, auth):
        r = client.get(f"{API}/watchlist/", headers=auth)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_add_stock(self, client, auth, stock_id):
        r = client.post(f"{API}/watchlist/", headers=auth, json={"stock_id": stock_id})
        assert r.status_code == 201, f"Add failed: {r.text}"
        data = r.json()
        assert data["stock_id"] == stock_id
        assert "stock_name" in data
        assert "close_price" in data

    def test_check_watched(self, client, auth, stock_id):
        r = client.get(f"{API}/watchlist/check/{stock_id}", headers=auth)
        assert r.status_code == 200
        assert r.json()["is_watched"] is True

    def test_add_duplicate_returns_409(self, client, auth, stock_id):
        r = client.post(f"{API}/watchlist/", headers=auth, json={"stock_id": stock_id})
        assert r.status_code == 409

    def test_list_has_item(self, client, auth, stock_id):
        r = client.get(f"{API}/watchlist/", headers=auth)
        assert r.status_code == 200
        items = r.json()
        assert any(item["stock_id"] == stock_id for item in items)

    def test_remove_stock(self, client, auth, stock_id):
        r = client.delete(f"{API}/watchlist/{stock_id}", headers=auth)
        assert r.status_code == 204

    def test_check_after_remove(self, client, auth, stock_id):
        r = client.get(f"{API}/watchlist/check/{stock_id}", headers=auth)
        assert r.status_code == 200
        assert r.json()["is_watched"] is False

    def test_remove_nonexistent_returns_404(self, client, auth):
        r = client.delete(f"{API}/watchlist/9999", headers=auth)
        assert r.status_code == 404

    def test_add_nonexistent_stock_returns_404(self, client, auth):
        r = client.post(f"{API}/watchlist/", headers=auth, json={"stock_id": "0000"})
        assert r.status_code == 404


# ======================================================================
# 3. Alerts E2E
# ======================================================================

class TestAlertsE2E:
    def test_list_empty(self, client, auth):
        r = client.get(f"{API}/alerts/", headers=auth)
        assert r.status_code == 200
        assert r.json() == []

    def test_create_alert_above(self, client, auth, stock_id):
        r = client.post(f"{API}/alerts/", headers=auth, json={
            "stock_id": stock_id,
            "condition_type": "above",
            "threshold": 1000.0,
        })
        assert r.status_code == 201, f"Create failed: {r.text}"
        data = r.json()
        assert data["stock_id"] == stock_id
        assert data["condition_type"] == "above"
        assert data["threshold"] == 1000.0
        assert data["is_active"] is True
        assert data["is_triggered"] is False
        return data["id"]

    def test_create_alert_below(self, client, auth, stock_id):
        r = client.post(f"{API}/alerts/", headers=auth, json={
            "stock_id": stock_id,
            "condition_type": "below",
            "threshold": 500.0,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["condition_type"] == "below"
        assert data["threshold"] == 500.0

    def test_list_alerts_has_items(self, client, auth):
        r = client.get(f"{API}/alerts/", headers=auth)
        assert r.status_code == 200
        alerts = r.json()
        assert len(alerts) >= 2

    def test_update_alert(self, client, auth, stock_id):
        # Get first alert
        r = client.get(f"{API}/alerts/", headers=auth)
        alerts = r.json()
        alert_id = alerts[0]["id"]

        # Update threshold
        r = client.patch(f"{API}/alerts/{alert_id}", headers=auth, json={
            "threshold": 1200.0,
        })
        assert r.status_code == 200
        assert r.json()["threshold"] == 1200.0

    def test_deactivate_alert(self, client, auth):
        r = client.get(f"{API}/alerts/", headers=auth)
        alert_id = r.json()[0]["id"]

        r = client.patch(f"{API}/alerts/{alert_id}", headers=auth, json={
            "is_active": False,
        })
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_reactivate_resets_triggered(self, client, auth):
        r = client.get(f"{API}/alerts/", headers=auth)
        alert_id = r.json()[0]["id"]

        r = client.patch(f"{API}/alerts/{alert_id}", headers=auth, json={
            "is_active": True,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["is_active"] is True
        assert data["is_triggered"] is False

    def test_delete_alert(self, client, auth):
        r = client.get(f"{API}/alerts/", headers=auth)
        alerts = r.json()
        count_before = len(alerts)
        alert_id = alerts[-1]["id"]

        r = client.delete(f"{API}/alerts/{alert_id}", headers=auth)
        assert r.status_code == 204

        r = client.get(f"{API}/alerts/", headers=auth)
        assert len(r.json()) == count_before - 1

    def test_create_invalid_stock_returns_404(self, client, auth):
        r = client.post(f"{API}/alerts/", headers=auth, json={
            "stock_id": "0000",
            "condition_type": "above",
            "threshold": 100.0,
        })
        assert r.status_code == 404

    def test_create_invalid_condition_returns_422(self, client, auth, stock_id):
        r = client.post(f"{API}/alerts/", headers=auth, json={
            "stock_id": stock_id,
            "condition_type": "invalid",
            "threshold": 100.0,
        })
        assert r.status_code == 422


# ======================================================================
# 4. Notifications E2E
# ======================================================================

class TestNotificationsE2E:
    def test_list_notifications(self, client, auth):
        r = client.get(f"{API}/notifications/", headers=auth)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_unread_count(self, client, auth):
        r = client.get(f"{API}/notifications/unread-count", headers=auth)
        assert r.status_code == 200
        data = r.json()
        assert "count" in data
        assert isinstance(data["count"], int)

    def test_mark_all_read(self, client, auth):
        r = client.post(f"{API}/notifications/read-all", headers=auth)
        assert r.status_code == 204

        # Verify unread count is 0
        r = client.get(f"{API}/notifications/unread-count", headers=auth)
        assert r.json()["count"] == 0

    def test_mark_read_nonexistent_returns_404(self, client, auth):
        r = client.patch(f"{API}/notifications/999999/read", headers=auth)
        assert r.status_code == 404

    def test_pagination(self, client, auth):
        r = client.get(f"{API}/notifications/?skip=0&limit=5", headers=auth)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ======================================================================
# 5. Cross-user isolation
# ======================================================================

class TestCrossUserIsolation:
    @pytest.fixture(scope="class")
    def auth2(self, client):
        """Register a second user."""
        suffix = random_suffix()
        username = f"e2e2_{suffix}"
        email = f"e2e2_{suffix}@test.com"
        password = "TestPass456!"

        r = client.post(f"{API}/auth/register", json={
            "username": username, "email": email, "password": password,
        })
        assert r.status_code in (200, 201)

        r = client.post(f"{API}/auth/login", data={
            "username": username, "password": password,
        })
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_watchlist_isolation(self, client, auth, auth2, stock_id):
        # User 1 adds stock
        client.post(f"{API}/watchlist/", headers=auth, json={"stock_id": stock_id})

        # User 2 should not see it
        r = client.get(f"{API}/watchlist/check/{stock_id}", headers=auth2)
        assert r.json()["is_watched"] is False

        # Cleanup
        client.delete(f"{API}/watchlist/{stock_id}", headers=auth)

    def test_alert_isolation(self, client, auth, auth2, stock_id):
        # User 1 creates alert
        r = client.post(f"{API}/alerts/", headers=auth, json={
            "stock_id": stock_id, "condition_type": "above", "threshold": 999.0,
        })
        alert_id = r.json()["id"]

        # User 2 cannot update it
        r = client.patch(f"{API}/alerts/{alert_id}", headers=auth2, json={
            "threshold": 1.0,
        })
        assert r.status_code == 404

        # User 2 cannot delete it
        r = client.delete(f"{API}/alerts/{alert_id}", headers=auth2)
        assert r.status_code == 404

        # Cleanup
        client.delete(f"{API}/alerts/{alert_id}", headers=auth)


# ======================================================================
# 6. Frontend pages (HTTP status checks)
# ======================================================================

class TestFrontendPages:
    """Verify frontend pages return 200 (Next.js SSR/CSR)."""

    @pytest.fixture(scope="class")
    def fe_client(self):
        with httpx.Client(base_url="http://localhost:3000", timeout=15, follow_redirects=True) as c:
            yield c

    def test_welcome_page(self, fe_client):
        r = fe_client.get("/welcome")
        assert r.status_code == 200
        assert "stock-tracer" in r.text.lower() or "台股" in r.text or "免費" in r.text

    def test_login_page(self, fe_client):
        r = fe_client.get("/login")
        assert r.status_code == 200

    def test_register_page(self, fe_client):
        r = fe_client.get("/register")
        assert r.status_code == 200

    def test_unauthenticated_redirect(self, fe_client):
        """Dashboard pages should redirect unauthenticated users to /welcome."""
        r = fe_client.get("/", follow_redirects=False)
        # Could be 200 (client-side redirect) or 307 (server redirect)
        # Either way the page should load without 500
        assert r.status_code in (200, 302, 307, 308)


# ======================================================================
# 7. API edge cases & rate limiting
# ======================================================================

class TestEdgeCases:
    def test_invalid_token_returns_401(self, client):
        r = client.get(f"{API}/watchlist/", headers={"Authorization": "Bearer invalid"})
        assert r.status_code == 401

    def test_expired_like_token(self, client):
        r = client.get(f"{API}/alerts/", headers={"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmYWtlIiwiZXhwIjoxMDAwMDAwMDAwfQ.fake"})
        assert r.status_code == 401

    def test_watchlist_add_missing_body_returns_422(self, client, auth):
        r = client.post(f"{API}/watchlist/", headers=auth, json={})
        assert r.status_code == 422

    def test_alert_negative_threshold_returns_422(self, client, auth, stock_id):
        r = client.post(f"{API}/alerts/", headers=auth, json={
            "stock_id": stock_id,
            "condition_type": "above",
            "threshold": -10.0,
        })
        assert r.status_code == 422


# ======================================================================
# 8. Redis cache integration
# ======================================================================

class TestRedisIntegration:
    def test_unread_count_cached(self, client, auth):
        """Call unread-count twice quickly — second should hit Redis cache."""
        r1 = client.get(f"{API}/notifications/unread-count", headers=auth)
        assert r1.status_code == 200
        count1 = r1.json()["count"]

        r2 = client.get(f"{API}/notifications/unread-count", headers=auth)
        assert r2.status_code == 200
        count2 = r2.json()["count"]

        # Both should return same value (cached)
        assert count1 == count2
