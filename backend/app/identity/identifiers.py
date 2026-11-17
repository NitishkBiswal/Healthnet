"""AES-256-GCM encryption helpers for sensitive patient identifiers."""

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_AAD = b"healthnet:aadhaar:v1"


def _aadhaar_key() -> bytes:
    # Production deployments should set a dedicated AADHAAR_ENCRYPTION_KEY.
    # The SECRET_KEY fallback keeps local development runnable, but must be replaced.
    secret = settings.AADHAAR_ENCRYPTION_KEY or settings.SECRET_KEY
    return hashlib.sha256(("healthnet:aadhaar:v1:" + secret).encode()).digest()


def encrypt_aadhaar(value: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_aadhaar_key()).encrypt(nonce, value.encode("ascii"), _AAD)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_aadhaar(value: str) -> str:
    payload = base64.urlsafe_b64decode(value.encode("ascii"))
    nonce, ciphertext = payload[:12], payload[12:]
    return AESGCM(_aadhaar_key()).decrypt(nonce, ciphertext, _AAD).decode("ascii")
