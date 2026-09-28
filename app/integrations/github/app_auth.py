from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jose import JWTError, jwt

from app.config import Settings, get_settings
from app.integrations.github.errors import GithubAPIError

API_BASE = "https://api.github.com"
OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
STATE_TTL_MINUTES = 15
TOKEN_REFRESH_MARGIN = timedelta(minutes=2)

_token_cache: dict[int, tuple[str, datetime]] = {}
_token_lock = threading.Lock()


def app_jwt(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if not settings.github_app_id or not settings.github_app_private_key:
        raise GithubAPIError("GitHub App is not configured", status_code=503)
    now = datetime.now(UTC)
    payload = {
        "iat": int((now - timedelta(seconds=60)).timestamp()),
        "exp": int((now + timedelta(minutes=9)).timestamp()),
        "iss": settings.github_app_id,
    }
    try:
        return jwt.encode(payload, settings.github_private_key_pem, algorithm="RS256")
    except JWTError as exc:
        raise GithubAPIError("Invalid GitHub App private key", status_code=503) from exc


def _parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def installation_token(installation_id: int, settings: Settings | None = None) -> str:
    now = datetime.now(UTC)
    with _token_lock:
        cached = _token_cache.get(installation_id)
        if cached and cached[1] - TOKEN_REFRESH_MARGIN > now:
            return cached[0]

    try:
        response = httpx.post(
            f"{API_BASE}/app/installations/{installation_id}/access_tokens",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {app_jwt(settings)}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        raise GithubAPIError(f"GitHub installation token request failed: {exc}") from exc

    if response.status_code >= 400:
        raise GithubAPIError(
            "Failed to create GitHub installation token",
            status_code=response.status_code,
            body=response.text,
        )
    data = response.json()
    token = data["token"]
    expires_at = _parse_github_datetime(data.get("expires_at")) or now + timedelta(minutes=55)
    with _token_lock:
        _token_cache[installation_id] = (token, expires_at)
    return token


def forget_installation_token(installation_id: int) -> None:
    with _token_lock:
        _token_cache.pop(installation_id, None)


def build_install_url(state: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return f"https://github.com/apps/{settings.github_app_slug}/installations/new?{urlencode({'state': state})}"


def create_install_state(organization_id: UUID, user_id: UUID, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    payload = {
        "purpose": "github_install",
        "organization_id": str(organization_id),
        "user_id": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=STATE_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def parse_install_state(state: str, settings: Settings | None = None) -> tuple[UUID, UUID]:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise GithubAPIError("Invalid or expired install state", status_code=400) from exc
    if payload.get("purpose") != "github_install":
        raise GithubAPIError("Invalid install state", status_code=400)
    try:
        return UUID(payload["organization_id"]), UUID(payload["user_id"])
    except (KeyError, ValueError) as exc:
        raise GithubAPIError("Invalid install state payload", status_code=400) from exc


def exchange_user_code(code: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    try:
        response = httpx.post(
            OAUTH_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        raise GithubAPIError(f"GitHub OAuth token request failed: {exc}") from exc

    data: dict[str, Any] = response.json() if response.content else {}
    if response.status_code >= 400 or data.get("error") or not data.get("access_token"):
        raise GithubAPIError(
            f"GitHub OAuth code exchange failed: {data.get('error_description') or data.get('error') or response.status_code}",
            status_code=400,
            body=response.text,
        )
    return str(data["access_token"])
