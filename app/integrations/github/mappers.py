from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.models.enums import PullRequestStatus

JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
MAX_JIRA_KEYS = 20


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_jira_keys(*texts: str | None, project_key: str | None = None) -> list[str]:
    prefix = f"{project_key.upper()}-" if project_key else None
    keys: list[str] = []
    for text in texts:
        if not text:
            continue
        for match in JIRA_KEY_RE.findall(text.upper() if prefix else text):
            if prefix and not match.startswith(prefix):
                continue
            if match not in keys:
                keys.append(match)
            if len(keys) >= MAX_JIRA_KEYS:
                return keys
    return keys


def pull_request_status(pr: dict[str, Any]) -> PullRequestStatus:
    if pr.get("merged_at") or pr.get("merged"):
        return PullRequestStatus.merged
    if pr.get("state") == "closed":
        return PullRequestStatus.closed
    return PullRequestStatus.open


def map_pull_request(pr: dict[str, Any], project_key: str | None) -> dict[str, Any]:
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    user = pr.get("user") or {}
    title = str(pr.get("title") or f"PR #{pr.get('number')}")
    return {
        "number": pr.get("number"),
        "github_id": pr.get("id"),
        "title": title[:512],
        "url": pr.get("html_url"),
        "status": pull_request_status(pr),
        "draft": bool(pr.get("draft")),
        "author_login": user.get("login"),
        "head_branch": head.get("ref"),
        "base_branch": base.get("ref"),
        "opened_at": parse_datetime(pr.get("created_at")),
        "merged_at": parse_datetime(pr.get("merged_at")),
        "closed_at": parse_datetime(pr.get("closed_at")),
        "github_updated_at": parse_datetime(pr.get("updated_at")),
        "jira_keys": extract_jira_keys(title, head.get("ref"), pr.get("body"), project_key=project_key),
    }


def map_commit(item: dict[str, Any], project_key: str | None) -> dict[str, Any]:
    """Map a commit from the REST `GET /repos/{repo}/commits` list."""
    commit = item.get("commit") or {}
    author = commit.get("author") or {}
    message = commit.get("message")
    return {
        "sha": str(item.get("sha")),
        "message": message,
        "url": item.get("html_url"),
        "author_login": (item.get("author") or {}).get("login"),
        "author_name": author.get("name"),
        "committed_at": parse_datetime(author.get("date")),
        "jira_keys": extract_jira_keys(message, project_key=project_key),
    }


def map_push_commit(item: dict[str, Any], project_key: str | None) -> dict[str, Any]:
    """Map a commit from a `push` webhook payload."""
    author = item.get("author") or {}
    message = item.get("message")
    return {
        "sha": str(item.get("id")),
        "message": message,
        "url": item.get("url"),
        "author_login": author.get("username"),
        "author_name": author.get("name"),
        "committed_at": parse_datetime(item.get("timestamp")),
        "jira_keys": extract_jira_keys(message, project_key=project_key),
    }
