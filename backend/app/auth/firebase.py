import logging

import firebase_admin
from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)

_initialized = False


def _ensure_initialized():
    """Initialize Firebase Admin SDK if not already done."""
    global _initialized
    if _initialized:
        return True

    if firebase_admin._apps:
        _initialized = True
        return True

    try:
        # In GCP (Cloud Run), uses Application Default Credentials
        # Locally, uses GOOGLE_APPLICATION_CREDENTIALS env var
        firebase_admin.initialize_app()
        _initialized = True
        logger.info("Firebase Admin SDK initialized")
        return True
    except Exception as e:
        logger.warning(f"Firebase Admin SDK not initialized: {e}")
        return False


async def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return decoded claims."""
    if not _ensure_initialized():
        raise ValueError(
            "Firebase not configured — set GOOGLE_APPLICATION_CREDENTIALS "
            "or deploy to GCP with Application Default Credentials"
        )
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception as e:
        raise ValueError(f"Invalid token: {e}") from None
