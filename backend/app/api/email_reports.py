"""API endpoint for testing email report delivery."""

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.models.user import User
from app.tasks.email_report import send_user_report

router = APIRouter()


@router.post("/test-send")
async def test_send_report(current_user: User = Depends(get_current_user)):
    """Send a test daily report to the current user immediately."""
    send_user_report.delay(user_id=current_user.id)
    return {"status": "queued", "email": current_user.email}
