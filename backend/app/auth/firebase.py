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
        import os

        from app.config import settings

        project_id = (
            settings.firebase_project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCLOUD_PROJECT")
        )

        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            # Verify the key file is readable
            with open(cred_path) as f:
                import json as _json
                key_data = _json.load(f)
            logger.info(
                "SA key file: type=%s, project=%s, "
                "client=%s, size=%d bytes",
                key_data.get("type"),
                key_data.get("project_id"),
                key_data.get("client_email", "")[:30],
                os.path.getsize(cred_path),
            )
            cred = firebase_admin.credentials.Certificate(cred_path)
            logger.info(
                "Initializing Firebase with SA key file, "
                "project=%s",
                project_id,
            )
        else:
            cred = firebase_admin.credentials.ApplicationDefault()
            logger.info(
                "Initializing Firebase with ADC, project=%s",
                project_id,
            )

        firebase_admin.initialize_app(
            credential=cred,
            options={"projectId": project_id} if project_id else None,
        )
        _initialized = True
        logger.info("Firebase Admin SDK initialized")
        return True
    except Exception as e:
        logger.warning(f"Firebase Admin SDK not initialized: {e}")
        return False


def delete_firebase_user(email: str) -> bool:
    """Delete a Firebase Auth user by email. Returns True if deleted, False if not found."""
    if not _ensure_initialized():
        logger.warning("Firebase not configured — skipping auth user deletion")
        return False
    try:
        user = firebase_auth.get_user_by_email(email)
        firebase_auth.delete_user(user.uid)
        logger.info(f"Firebase Auth user deleted: {email} (uid={user.uid})")
        return True
    except firebase_auth.UserNotFoundError:
        logger.info(f"Firebase Auth user not found: {email}")
        return False
    except Exception:
        logger.exception(f"Failed to delete Firebase Auth user: {email}")
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
