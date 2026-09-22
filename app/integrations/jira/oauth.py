from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jose import JWTError, jwt

from app.config import JIRA_OAUTH_SCOPES, Settings, get_settings
from app.integrations.jira.errors import JiraAPIError

AUTH_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
STATE_TTL_MINUTES = 15


def build_authorize_url(state: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.jira_oauth_client_id,
        "scope": JIRA_OAUTH_SCOPES,
        "redirect_uri": settings.jira_oauth_redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def create_oauth_state(project_id: UUID, user_id: UUID, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=STATE_TTL_MINUTES)
    payload = {
        "purpose": "jira_oauth",
        "project_id": str(project_id),
        "user_id": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def parse_oauth_state(state: str, settings: Settings | None = None) -> tuple[UUID, UUID]:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise JiraAPIError("Invalid or expired OAuth state", status_code=400) from exc
    if payload.get("purpose") != "jira_oauth":
        raise JiraAPIError("Invalid OAuth state", status_code=400)
    try:
        return UUID(payload["project_id"]), UUID(payload["user_id"])
    except (KeyError, ValueError) as exc:
        raise JiraAPIError("Invalid OAuth state payload", status_code=400) from exc


def exchange_code(code: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.jira_oauth_client_id,
        "client_secret": settings.jira_oauth_client_secret,
        "code": code,
        "redirect_uri": settings.jira_oauth_redirect_uri,
    }
    return _token_request(data)


def refresh_tokens(refresh_token: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    data = {
        "grant_type": "refresh_token",
        "client_id": settings.jira_oauth_client_id,
        "client_secret": settings.jira_oauth_client_secret,
        "refresh_token": refresh_token,
    }
    return _token_request(data)


def _token_request(data: dict[str, str]) -> dict[str, Any]:
    try:
        response = httpx.post(
            TOKEN_URL,
            json=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        raise JiraAPIError(f"Jira OAuth token request failed: {exc}") from exc

    if response.status_code >= 400:
        raise JiraAPIError(
            "Jira OAuth token exchange failed",
            status_code=response.status_code,
            body=response.text,
        )
    return response.json()


def accessible_resources(access_token: str) -> list[dict[str, Any]]:
    try:
        response = httpx.get(
            RESOURCES_URL,
            headers={"Accept": "application/json", "Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        raise JiraAPIError(f"Failed to load Atlassian sites: {exc}") from exc

    if response.status_code in (401, 403):
        raise JiraAPIError("Jira auth failed", status_code=response.status_code, body=response.text)
    if response.status_code >= 400:
        raise JiraAPIError(
            "Failed to load Atlassian sites",
            status_code=response.status_code,
            body=response.text,
        )
    data = response.json()
    return list(data or [])


def token_expiry(expires_in: int | None) -> datetime:
    seconds = int(expires_in or 3600)
    return datetime.now(UTC) + timedelta(seconds=max(seconds - 60, 60))
