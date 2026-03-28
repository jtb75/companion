import firebase_admin
from firebase_admin import auth as firebase_auth

# Initialize Firebase Admin SDK
# In production, uses Application Default Credentials
# In development, can use GOOGLE_APPLICATION_CREDENTIALS env var
if not firebase_admin._apps:
    firebase_admin.initialize_app()


async def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return decoded claims."""
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception as e:
        raise ValueError(f"Invalid token: {e}") from None
