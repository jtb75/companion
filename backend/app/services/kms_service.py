"""Service for field-level encryption using Google Cloud KMS."""

import base64
import logging
from functools import lru_cache

from google.cloud import kms

from app.config import settings

logger = logging.getLogger(__name__)

class KMSService:
    def __init__(self):
        self.client = kms.KeyManagementServiceClient()
        self.key_name = settings.kms_key_id

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return a base64-encoded ciphertext."""
        if not self.key_name or settings.environment in ("development", "test"):
            # Fallback for local dev without KMS
            return f"enc:{plaintext}"

        try:
            response = self.client.encrypt(
                request={
                    "name": self.key_name,
                    "plaintext": plaintext.encode("utf-8"),
                }
            )
            return base64.b64encode(response.ciphertext).decode("utf-8")
        except Exception:
            logger.exception("KMS encryption failed")
            raise

    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt a base64-encoded ciphertext."""
        if not self.key_name or settings.environment in ("development", "test"):
            # Fallback for local dev without KMS
            if ciphertext_b64.startswith("enc:"):
                return ciphertext_b64[4:]
            return ciphertext_b64

        try:
            ciphertext = base64.b64decode(ciphertext_b64)
            response = self.client.decrypt(
                request={
                    "name": self.key_name,
                    "ciphertext": ciphertext,
                }
            )
            return response.plaintext.decode("utf-8")
        except Exception:
            logger.exception("KMS decryption failed")
            raise

@lru_cache
def get_kms_service() -> KMSService:
    return KMSService()
