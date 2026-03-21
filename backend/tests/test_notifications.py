import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestNotificationsCRUD:
    """Test notification endpoints."""

    async def _create_notification(self, db_session, user_id, title="Test", message="msg", is_read=False):
        from app.models.notification import Notification
        notif = Notification(
            user_id=user_id, title=title, message=message, is_read=is_read
        )
        db_session.add(notif)
        await db_session.commit()
        await db_session.refresh(notif)
        return notif

    async def test_list_empty(self, client: AsyncClient, auth_headers, test_user):
        res = await client.get("/api/v1/notifications/", headers=auth_headers)
        assert res.status_code == 200
        assert res.json() == []

    async def test_list_with_items(self, client: AsyncClient, auth_headers, test_user, db_session):
        user, _ = test_user
        await self._create_notification(db_session, user.id, "Alert 1", "Price hit")
        await self._create_notification(db_session, user.id, "Alert 2", "Price hit again")

        res = await client.get("/api/v1/notifications/", headers=auth_headers)
        assert len(res.json()) == 2

    async def test_list_pagination(self, client: AsyncClient, auth_headers, test_user, db_session):
        user, _ = test_user
        for i in range(5):
            await self._create_notification(db_session, user.id, f"Alert {i}")

        res = await client.get("/api/v1/notifications/", headers=auth_headers, params={"skip": 2, "limit": 2})
        assert len(res.json()) == 2

    async def test_unread_count(self, client: AsyncClient, auth_headers, test_user, db_session):
        user, _ = test_user
        await self._create_notification(db_session, user.id, "Unread 1", is_read=False)
        await self._create_notification(db_session, user.id, "Unread 2", is_read=False)
        await self._create_notification(db_session, user.id, "Read 1", is_read=True)

        res = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["count"] == 2

    async def test_mark_read(self, client: AsyncClient, auth_headers, test_user, db_session):
        user, _ = test_user
        notif = await self._create_notification(db_session, user.id, "Unread")

        res = await client.patch(f"/api/v1/notifications/{notif.id}/read", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["is_read"] is True

    async def test_mark_read_nonexistent(self, client: AsyncClient, auth_headers, test_user):
        res = await client.patch("/api/v1/notifications/99999/read", headers=auth_headers)
        assert res.status_code == 404

    async def test_mark_all_read(self, client: AsyncClient, auth_headers, test_user, db_session):
        user, _ = test_user
        await self._create_notification(db_session, user.id, "Unread 1")
        await self._create_notification(db_session, user.id, "Unread 2")

        res = await client.post("/api/v1/notifications/read-all", headers=auth_headers)
        assert res.status_code == 204

        # Verify all read
        res = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
        assert res.json()["count"] == 0


@pytest.mark.asyncio
class TestNotificationsAuth:
    """Test notification auth and isolation."""

    async def test_no_auth(self, client: AsyncClient):
        assert (await client.get("/api/v1/notifications/")).status_code == 401
        assert (await client.get("/api/v1/notifications/unread-count")).status_code == 401

    async def test_cross_user_isolation(self, client: AsyncClient, auth_headers, other_auth_headers, test_user, other_user, db_session):
        user, _ = test_user
        from app.models.notification import Notification
        notif = Notification(user_id=user.id, title="Secret", message="msg")
        db_session.add(notif)
        await db_session.commit()
        await db_session.refresh(notif)

        # Other user cannot see
        res = await client.get("/api/v1/notifications/", headers=other_auth_headers)
        assert res.json() == []

        # Other user cannot mark read
        res = await client.patch(f"/api/v1/notifications/{notif.id}/read", headers=other_auth_headers)
        assert res.status_code == 404

    async def test_cross_user_unread_count(self, client: AsyncClient, auth_headers, other_auth_headers, test_user, other_user, db_session):
        user, _ = test_user
        from app.models.notification import Notification
        db_session.add(Notification(user_id=user.id, title="X", message="y"))
        await db_session.commit()

        res = await client.get("/api/v1/notifications/unread-count", headers=other_auth_headers)
        assert res.json()["count"] == 0
