"""SQLAlchemy custom type for transparent field-level encryption."""

import json
from typing import Any

from sqlalchemy import Text, TypeDecorator

from app.services.kms_service import get_kms_service


class EncryptedText(TypeDecorator):
    """Transparently encrypts/decrypts text columns using Cloud KMS."""

    impl = Text
    cache_ok = False

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return get_kms_service().encrypt(value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return get_kms_service().decrypt(value)


class EncryptedJSON(TypeDecorator):
    """Transparently encrypts/decrypts JSON columns using Cloud KMS."""

    impl = Text # Store encrypted JSON as Text
    cache_ok = False

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        plaintext = json.dumps(value)
        return get_kms_service().encrypt(plaintext)

    def process_result_value(self, value: str | None, dialect: Any) -> Any:
        if value is None:
            return None
        plaintext = get_kms_service().decrypt(value)
        return json.loads(plaintext)
