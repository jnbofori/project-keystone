from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings, get_settings


class TokenCryptoError(Exception):
    pass


def _fernet(settings: Settings | None = None) -> Fernet:
    settings = settings or get_settings()
    key = (settings.jira_token_encryption_key or "").strip()
    if not key:
        raise TokenCryptoError("JIRA_TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:  # noqa: BLE001
        raise TokenCryptoError("Invalid JIRA_TOKEN_ENCRYPTION_KEY (must be a Fernet key)") from exc


def encrypt_token(plaintext: str, settings: Settings | None = None) -> str:
    return _fernet(settings).encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str, settings: Settings | None = None) -> str:
    try:
        return _fernet(settings).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise TokenCryptoError("Failed to decrypt Jira token") from exc
