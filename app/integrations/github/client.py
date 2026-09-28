from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.integrations.github.app_auth import API_BASE, app_jwt, forget_installation_token, installation_token
from app.integrations.github.errors import GithubAPIError

PER_PAGE = 100


class GithubClient:
    def __init__(self, token: str, *, installation_id: int | None = None):
        self._installation_id = installation_id
        self._http = httpx.Client(
            base_url=API_BASE,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    @classmethod
    def for_installation(cls, installation_id: int, settings: Settings | None = None) -> GithubClient:
        return cls(installation_token(installation_id, settings or get_settings()), installation_id=installation_id)

    @classmethod
    def for_app(cls, settings: Settings | None = None) -> GithubClient:
        return cls(app_jwt(settings or get_settings()))

    @classmethod
    def for_user(cls, user_token: str) -> GithubClient:
        return cls(user_token)

    def __enter__(self) -> GithubClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._http.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            raise GithubAPIError(f"GitHub request failed: {exc}") from exc
        if response.status_code == 401 and self._installation_id is not None:
            forget_installation_token(self._installation_id)
        if response.status_code >= 400:
            message = "GitHub API error"
            try:
                message = response.json().get("message") or message
            except ValueError:
                pass
            raise GithubAPIError(message, status_code=response.status_code, body=response.text)
        return response

    def _paginate(self, path: str, params: dict[str, Any] | None = None, items_key: str | None = None) -> Iterator[dict[str, Any]]:
        url: str | None = path
        query: dict[str, Any] | None = {"per_page": PER_PAGE, **(params or {})}
        while url:
            response = self._request("GET", url, params=query)
            data = response.json()
            items = data.get(items_key, []) if items_key else data
            yield from items or []
            url = response.links.get("next", {}).get("url")
            query = None

    def get_installation(self, installation_id: int) -> dict[str, Any]:
        return self._request("GET", f"/app/installations/{installation_id}").json()

    def delete_installation(self, installation_id: int) -> None:
        self._request("DELETE", f"/app/installations/{installation_id}")

    def user_installations(self) -> list[dict[str, Any]]:
        return list(self._paginate("/user/installations", items_key="installations"))

    def list_installation_repos(self) -> list[dict[str, Any]]:
        return list(self._paginate("/installation/repositories", items_key="repositories"))

    def list_pulls(self, full_name: str, since: datetime) -> Iterator[dict[str, Any]]:
        params = {"state": "all", "sort": "updated", "direction": "desc"}
        for pr in self._paginate(f"/repos/{full_name}/pulls", params):
            updated = pr.get("updated_at")
            if updated and datetime.fromisoformat(updated.replace("Z", "+00:00")) < since:
                return
            yield pr

    def list_commits(self, full_name: str, branch: str | None, since: datetime) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"since": since.isoformat()}
        if branch:
            params["sha"] = branch
        yield from self._paginate(f"/repos/{full_name}/commits", params)
