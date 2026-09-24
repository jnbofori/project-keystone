from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.integrations.jira.crypto import decrypt_token, encrypt_token
from app.integrations.jira.errors import JiraAPIError
from app.integrations.jira.oauth import refresh_tokens, token_expiry
from app.models.jira_connection import JiraConnection


class JiraClient:
    """Sync client for Jira Cloud Platform (v3) and Software Agile (1.0) via OAuth 3LO."""

    def __init__(
        self,
        *,
        access_token: str,
        cloud_id: str,
        story_points_field: str | None = None,
        timeout: float = 60.0,
    ):
        if not access_token or not cloud_id:
            raise JiraAPIError("Jira OAuth access token and cloud_id are required")
        self._story_points_field = (story_points_field or "").strip() or None
        print("access_token", access_token)
        print("cloud_id", cloud_id)
        self._client = httpx.Client(
            base_url=f"https://api.atlassian.com/ex/jira/{cloud_id}",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=timeout,
        )

    @classmethod
    def from_connection(
        cls,
        db: Session,
        connection: JiraConnection,
        settings: Settings | None = None,
    ) -> JiraClient:
        settings = settings or get_settings()
        if not connection.cloud_id:
            raise JiraAPIError(
                "Jira site not selected for this project (PUT /projects/{id}/jira/cloud)",
                status_code=400,
            )

        access_token = decrypt_token(connection.access_token_encrypted, settings)
        refresh_token = decrypt_token(connection.refresh_token_encrypted, settings)

        expires_at = connection.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC) + timedelta(minutes=2):
            try:
                token_data = refresh_tokens(refresh_token, settings)
            except JiraAPIError:
                raise JiraAPIError(
                    "Jira OAuth token expired; reconnect via /projects/{id}/jira/oauth/start",
                    status_code=401,
                ) from None
            access_token = token_data["access_token"]
            new_refresh = token_data.get("refresh_token") or refresh_token
            connection.access_token_encrypted = encrypt_token(access_token, settings)
            connection.refresh_token_encrypted = encrypt_token(new_refresh, settings)
            connection.token_expires_at = token_expiry(token_data.get("expires_in"))
            if token_data.get("scope"):
                connection.scopes = token_data["scope"]
            db.add(connection)
            db.flush()

        return cls(
            access_token=access_token,
            cloud_id=connection.cloud_id,
            story_points_field=settings.jira_story_points_field or None,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> JiraClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise JiraAPIError(f"Jira request failed: {exc}") from exc

        if response.status_code in (401, 403):
            raise JiraAPIError("Jira auth failed", status_code=response.status_code, body=response.text)
        if response.status_code == 404:
            raise JiraAPIError("Jira resource not found", status_code=404, body=response.text)
        if response.status_code >= 400:
            raise JiraAPIError(
                f"Jira API error ({response.status_code})",
                status_code=response.status_code,
                body=response.text,
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def list_projects(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/rest/api/3/project/search", params={"maxResults": 100})
        if isinstance(data, list):
            return data
        return list(data.get("values") or [])

    def get_project(self, project_key_or_id: str) -> dict[str, Any]:
        return self._request("GET", f"/rest/api/3/project/{project_key_or_id}")

    def list_project_role_urls(self, project_key: str) -> dict[str, str]:
        print("list_project_role_urls", project_key)
        data = self._request("GET", f"/rest/api/3/project/{project_key}/role")
        return dict(data or {})

    def get_project_role(self, role_url: str) -> dict[str, Any]:
        if role_url.startswith("http"):
            # OAuth responses may return absolute URLs; convert to path under cloud base
            marker = "/rest/"
            idx = role_url.find(marker)
            if idx >= 0:
                return self._request("GET", role_url[idx:])
            raise JiraAPIError(f"Unsupported role URL: {role_url}", status_code=400)
        return self._request("GET", role_url)

    def list_fields(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/rest/api/3/field")
        return list(data or [])

    def resolve_story_points_field(self) -> str | None:
        if self._story_points_field:
            return self._story_points_field
        for field in self.list_fields():
            name = (field.get("name") or "").strip().lower()
            if name in ("story points", "story point estimate"):
                field_id = field.get("id")
                if isinstance(field_id, str):
                    self._story_points_field = field_id
                    return field_id
        return None

    def search_issues(
        self,
        jql: str,
        fields: list[str],
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        next_page_token: str | None = None

        while True:
            try:
                body: dict[str, Any] = {
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": fields,
                }
                if next_page_token:
                    body["nextPageToken"] = next_page_token
                data = self._request("POST", "/rest/api/3/search/jql", json=body)
                batch = list(data.get("issues") or [])
                issues.extend(batch)
                next_page_token = data.get("nextPageToken")
                if not next_page_token or not batch:
                    break
            except JiraAPIError as exc:
                if exc.status_code not in (404, 410) or issues:
                    if not issues and exc.status_code in (404, 410):
                        return self._search_issues_classic(jql, fields, max_results)
                    raise
                return self._search_issues_classic(jql, fields, max_results)

        return issues

    def _search_issues_classic(
        self,
        jql: str,
        fields: list[str],
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        start_at = 0
        while True:
            data = self._request(
                "GET",
                "/rest/api/3/search",
                params={
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": ",".join(fields),
                },
            )
            batch = list(data.get("issues") or [])
            issues.extend(batch)
            total = int(data.get("total") or 0)
            start_at += len(batch)
            if not batch or start_at >= total:
                break
        return issues

    def get_issue_changelog(self, issue_key: str, max_results: int = 100) -> list[dict[str, Any]]:
        histories: list[dict[str, Any]] = []
        start_at = 0
        while True:
            data = self._request(
                "GET",
                f"/rest/api/3/issue/{issue_key}/changelog",
                params={"startAt": start_at, "maxResults": max_results},
            )
            values = list(data.get("values") or [])
            histories.extend(values)
            total = int(data.get("total") or 0)
            start_at += len(values)
            if not values or start_at >= total:
                break
        return histories

    def list_boards(self, project_key_or_id: str) -> list[dict[str, Any]]:
        print("list_boards", project_key_or_id)
        boards: list[dict[str, Any]] = []
        start_at = 0
        max_results = 50
        while True:
            data = self._request(
                "GET",
                "/rest/agile/1.0/board",
                params={
                    "projectKeyOrId": project_key_or_id,
                    "startAt": start_at,
                    "maxResults": max_results,
                },
            )
            values = list(data.get("values") or [])
            boards.extend(values)
            if data.get("isLast", True) or not values:
                break
            start_at += len(values)
        return boards

    def list_board_sprints(self, board_id: int | str) -> list[dict[str, Any]]:
        sprints: list[dict[str, Any]] = []
        start_at = 0
        max_results = 50
        while True:
            try:
                data = self._request(
                    "GET",
                    f"/rest/agile/1.0/board/{board_id}/sprint",
                    params={"startAt": start_at, "maxResults": max_results},
                )
            except JiraAPIError as exc:
                if exc.status_code in (400, 404):
                    return sprints
                raise
            values = list(data.get("values") or [])
            sprints.extend(values)
            if data.get("isLast", True) or not values:
                break
            start_at += len(values)
        return sprints

    def register_webhooks(
        self,
        *,
        url: str,
        events: list[str],
        jql_filter: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/rest/api/3/webhook",
            json={
                "url": url,
                "webhooks": [
                    {
                        "events": events,
                        "jqlFilter": jql_filter,
                    }
                ],
            },
        )

    def delete_webhooks(self, webhook_ids: list[int | str]) -> None:
        ids = [int(wid) for wid in webhook_ids if wid is not None]
        if not ids:
            return
        self._request("DELETE", "/rest/api/3/webhook", json={"webhookIds": ids})
