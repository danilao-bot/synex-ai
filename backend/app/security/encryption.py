"""Symmetric encryption utilities for storing sensitive credentials at rest."""

import base64
import logging
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

# Ensure we have a valid key
try:
    key_bytes = settings.ENCRYPTION_KEY.encode("utf-8")
    # Verify/pad base64 key
    _fernet = Fernet(key_bytes)
except Exception as e:
    logger.warning("Invalid or malformed ENCRYPTION_KEY in configuration. Generating a temporary key for this session. %s", e)
    # Generate a random Fernet key on the fly if invalid
    _fernet = Fernet(Fernet.generate_key())


def encrypt_value(value: str | None) -> str | None:
    """Encrypt a plaintext string using Fernet symmetric encryption."""
    if not value:
        return None
    try:
        token = _fernet.encrypt(value.encode("utf-8"))
        return token.decode("utf-8")
    except Exception:
        logger.exception("Failed to encrypt value")
        return None


def decrypt_value(token: str | None) -> str | None:
    """Decrypt a ciphertext token back into the plaintext string."""
    if not token:
        return None
    try:
        # Check if the value is actually encrypted (Fernet tokens start with gAAAA)
        if not token.startswith("gAAAA"):
            return token  # Return as-is if it's already plaintext (e.g. legacy/mock keys)
        decrypted = _fernet.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        logger.warning("Decrypt failed, returning value as-is (might be legacy unencrypted key)")
        return token
