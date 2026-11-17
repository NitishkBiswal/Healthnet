"""Application-level encryption helpers for sensitive patient identifiers."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _aadhaar_cipher() -> Fernet:
    # Production deployments should set a dedicated AADHAAR_ENCRYPTION_KEY.
    # The SECRET_KEY fallback keeps local development runnable, but must be replaced.
    secret = settings.AADHAAR_ENCRYPTION_KEY or settings.SECRET_KEY
    derived = hashlib.sha256(("healthnet:aadhaar:v1:" + secret).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_aadhaar(value: str) -> str:
    return _aadhaar_cipher().encrypt(value.encode("ascii")).decode("ascii")


def decrypt_aadhaar(value: str) -> str:
    return _aadhaar_cipher().decrypt(value.encode("ascii")).decode("ascii")
