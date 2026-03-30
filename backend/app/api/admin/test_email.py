"""Admin API — Test email sending."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import AdminUser, require_admin_role
from app.integrations.email_service import send_email

_admin = require_admin_role("admin")

router = APIRouter(tags=["Admin - Test"])


@router.post("/admin/test-email")
async def test_email(
    data: dict,
    admin: AdminUser = Depends(_admin),
):
    """Send a test email (admin only)."""
    success = await send_email(
        to_email=data.get("to", admin.email),
        to_name=data.get("name", "Test User"),
        subject=data.get("subject", "D.D. Companion Test Email"),
        text_body=data.get("body", "This is a test email from D.D. Companion."),
    )
    return {"sent": success}
