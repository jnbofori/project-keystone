from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.github.app_auth import forget_installation_token
from app.integrations.github.mappers import map_pull_request, map_push_commit
from app.integrations.github.sync import upsert_commit, upsert_pull_request
from app.models.github_installation import GithubInstallation
from app.models.project_github_repo import ProjectGithubRepo

logger = logging.getLogger(__name__)


def verify_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


def _installation_row(db: Session, payload: dict[str, Any]) -> GithubInstallation | None:
    installation_id = (payload.get("installation") or {}).get("id")
    if installation_id is None:
        return None
    return db.query(GithubInstallation).filter(GithubInstallation.installation_id == int(installation_id)).first()


def _links_for_repo(db: Session, payload: dict[str, Any]) -> list[ProjectGithubRepo]:
    repo_id = (payload.get("repository") or {}).get("id")
    if repo_id is None:
        return []
    query = db.query(ProjectGithubRepo).filter(ProjectGithubRepo.repo_id == int(repo_id))
    installation = _installation_row(db, payload)
    if installation is not None:
        query = query.filter(ProjectGithubRepo.installation_id == installation.id)
    return query.all()


def _handle_installation(db: Session, action: str | None, payload: dict[str, Any]) -> str:
    installation = _installation_row(db, payload)
    if installation is None:
        return "ignored"
    if action == "deleted":
        forget_installation_token(installation.installation_id)
        db.delete(installation)
    elif action == "suspend":
        installation.suspended_at = datetime.now(UTC)
        forget_installation_token(installation.installation_id)
    elif action == "unsuspend":
        installation.suspended_at = None
    else:
        return "ignored"
    db.commit()
    return "ok"


def _handle_installation_repositories(db: Session, action: str | None, payload: dict[str, Any]) -> str:
    installation = _installation_row(db, payload)
    if installation is None:
        return "ignored"
    selection = payload.get("repository_selection")
    if selection:
        installation.repository_selection = selection
    if action == "removed":
        repo_ids = [int(r["id"]) for r in payload.get("repositories_removed") or [] if r.get("id") is not None]
        if repo_ids:
            (
                db.query(ProjectGithubRepo)
                .filter(
                    ProjectGithubRepo.installation_id == installation.id,
                    ProjectGithubRepo.repo_id.in_(repo_ids),
                )
                .delete(synchronize_session=False)
            )
    db.commit()
    return "ok"


def _handle_pull_request(db: Session, payload: dict[str, Any]) -> str:
    pr = payload.get("pull_request") or {}
    if pr.get("number") is None:
        return "ignored"
    links = _links_for_repo(db, payload)
    if not links:
        return "ignored"
    for link in links:
        upsert_pull_request(db, link.project, link, map_pull_request(pr, link.project.jira_project_key))
    db.commit()
    return "ok"


def _handle_push(db: Session, payload: dict[str, Any]) -> str:
    links = _links_for_repo(db, payload)
    if not links:
        return "ignored"
    ref = str(payload.get("ref") or "")
    handled = False
    for link in links:
        default_branch = link.default_branch or (payload.get("repository") or {}).get("default_branch")
        if default_branch and ref != f"refs/heads/{default_branch}":
            continue
        for item in payload.get("commits") or []:
            if item.get("id"):
                upsert_commit(db, link.project, link, map_push_commit(item, link.project.jira_project_key))
                handled = True
    if not handled:
        return "ignored"
    db.commit()
    return "ok"


def handle_event(db: Session, event: str, payload: dict[str, Any]) -> str:
    action = payload.get("action")
    if event == "installation":
        return _handle_installation(db, action, payload)
    if event == "installation_repositories":
        return _handle_installation_repositories(db, action, payload)
    if event == "pull_request":
        return _handle_pull_request(db, payload)
    if event == "push":
        return _handle_push(db, payload)
    return "ignored"
