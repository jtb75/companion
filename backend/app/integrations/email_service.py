"""Email service using Mailjet.

Sends transactional emails for:
- Caregiver invitations
- Welcome emails after profile completion
- Safety alerts to caregivers
"""

import logging

from app.branding import (
    BRAND_DOMAIN,
    BRAND_EMAIL_FROM_ADDRESS,
    BRAND_EMAIL_FROM_NAME,
    BRAND_MID,
    BRAND_SHORT,
)
from app.config import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Get Mailjet client. Returns None if not configured."""
    if not settings.mailjet_api_key or not settings.mailjet_secret_key:
        logger.warning("Mailjet not configured — emails will be logged only")
        return None
    try:
        from mailjet_rest import Client
        return Client(
            auth=(settings.mailjet_api_key, settings.mailjet_secret_key),
            version='v3.1',
        )
    except Exception:
        logger.exception("Failed to create Mailjet client")
        return None


async def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> bool:
    """Send a single email via Mailjet."""
    client = _get_client()

    message = {
        "From": {
            "Email": BRAND_EMAIL_FROM_ADDRESS,
            "Name": BRAND_EMAIL_FROM_NAME,
        },
        "To": [{"Email": to_email, "Name": to_name}],
        "Subject": subject,
        "TextPart": text_body,
    }
    if html_body:
        message["HTMLPart"] = html_body

    if client is None:
        logger.info(
            f"Email (no client): to={to_email} "
            f"subject=\"{subject}\""
        )
        return True  # Pretend success in dev

    try:
        result = client.send.create(data={"Messages": [message]})
        status = result.status_code
        if status == 200:
            logger.info(f"Email sent: to={to_email} subject=\"{subject}\"")
            return True
        else:
            logger.error(
                f"Mailjet error {status}: {result.json()}"
            )
            return False
    except Exception:
        logger.exception(f"Failed to send email to {to_email}")
        return False


async def send_caregiver_invitation(
    to_email: str,
    to_name: str,
    user_name: str,
    relationship: str,
    invited_by: str,
) -> bool:
    """Send a caregiver invitation email."""
    subject = f"You've been invited to {BRAND_MID}"

    text_body = (
        f"Hi {to_name},\n\n"
        f"{invited_by} has invited you as a {relationship} "
        f"for {user_name} on {BRAND_MID}.\n\n"
        f"To get started, visit the {BRAND_SHORT} dashboard "
        f"and sign in with your Google account ({to_email}).\n\n"
        f"— The {BRAND_SHORT} Team"
    )

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 32px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px;">🌟</span>
            <h1 style="color: #2C5F8A; font-size: 22px; margin: 8px 0 0;">{BRAND_MID}</h1>
        </div>
        <p>Hi {to_name},</p>
        <p><strong>{invited_by}</strong> has invited you as a <strong>{relationship}</strong> for <strong>{user_name}</strong> on {BRAND_MID}.</p>
        <p>As a caregiver, you'll be able to view {user_name}'s status, upcoming appointments, and important alerts.</p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="https://app.{BRAND_DOMAIN}"
               style="background: #2C5F8A; color: white; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; display: inline-block;">
                Sign In to {BRAND_SHORT}
            </a>
        </div>
        <p style="color: #888; font-size: 13px;">Sign in with your Google account ({to_email}) to get started.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
        <p style="color: #aaa; font-size: 12px; text-align: center;">— The {BRAND_SHORT} Team</p>
    </div>
    """

    return await send_email(to_email, to_name, subject, text_body, html_body)


async def send_welcome(
    to_email: str,
    to_name: str,
) -> bool:
    """Send a welcome email after profile completion."""
    subject = f"Welcome to {BRAND_MID}"

    text_body = (
        f"Hi {to_name},\n\n"
        f"Welcome to {BRAND_MID}! Your profile is all set.\n\n"
        f"{BRAND_SHORT} is here to help you stay on top of things — "
        f"your mail, appointments, medications, and whatever else you need.\n\n"
        f"— {BRAND_SHORT}"
    )

    return await send_email(to_email, to_name, subject, text_body)


async def send_safety_alert(
    to_email: str,
    to_name: str,
    user_name: str,
    alert_type: str,
    alert_message: str,
) -> bool:
    """Send a safety alert to a caregiver."""
    subject = f"{BRAND_SHORT} Alert: {user_name}"

    text_body = (
        f"Hi {to_name},\n\n"
        f"This is an alert about {user_name}:\n\n"
        f"{alert_message}\n\n"
        f"You may want to check in with {user_name}.\n\n"
        f"— {BRAND_SHORT}"
    )

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 32px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <span style="font-size: 36px;">🌟</span>
            <h1 style="color: #2C5F8A; font-size: 22px; margin: 8px 0 0;">{BRAND_MID}</h1>
        </div>
        <div style="background: #FDF3E7; border: 1px solid #D4832A33; border-radius: 12px; padding: 16px; margin: 16px 0;">
            <p style="margin: 0; font-weight: 600; color: #D4832A;">⚠️ Alert about {user_name}</p>
            <p style="margin: 8px 0 0; color: #4A4A6A;">{alert_message}</p>
        </div>
        <p>You may want to check in with {user_name}.</p>
        <div style="text-align: center; margin: 24px 0;">
            <a href="https://app.{BRAND_DOMAIN}"
               style="background: #2C5F8A; color: white; padding: 12px 24px; border-radius: 12px; text-decoration: none; font-weight: 600; display: inline-block;">
                View Dashboard
            </a>
        </div>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
        <p style="color: #aaa; font-size: 12px; text-align: center;">— The {BRAND_SHORT} Team</p>
    </div>
    """

    return await send_email(to_email, to_name, subject, text_body, html_body)
