from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.github.client import GithubClient
from app.integrations.github.errors import GithubAPIError
from app.integrations.github.mappers import map_commit, map_pull_request
from app.models.commit import Commit
from app.models.enums import IntegrationSource
from app.models.project import Project
from app.models.project_github_repo import ProjectGithubRepo
from app.models.pull_request import PullRequest
from app.models.task import Task

logger = logging.getLogger(__name__)

SYNC_LOOKBACK_DAYS = 90


@dataclass
class GithubSyncError:
    repo: str
    message: str


@dataclass
class GithubSyncResult:
    project_id: Any
    repos: int = 0
    pull_requests: int = 0
    commits: int = 0
    errors: list[GithubSyncError] = field(default_factory=list)


def _task_id_for_keys(db: Session, project: Project, keys: list[str]) -> Any:
    if not keys:
        return None
    task = (
        db.query(Task)
        .filter(Task.project_id == project.id, Task.external_key.in_(keys))
        .order_by(Task.created_at)
        .first()
    )
    return task.id if task else None


def upsert_pull_request(db: Session, project: Project, repo_link: ProjectGithubRepo, data: dict[str, Any]) -> PullRequest:
    external_key = f"{repo_link.full_name}#{data['number']}"
    pr = (
        db.query(PullRequest)
        .filter(
            PullRequest.project_id == project.id,
            PullRequest.source == IntegrationSource.github,
            PullRequest.external_key == external_key,
        )
        .first()
    )
    if pr is None:
        pr = PullRequest(project_id=project.id, source=IntegrationSource.github, external_key=external_key)
    for key, value in data.items():
        setattr(pr, key, value)
    pr.repo_link_id = repo_link.id
    pr.task_id = _task_id_for_keys(db, project, data.get("jira_keys") or []) or pr.task_id
    db.add(pr)
    return pr


def upsert_commit(db: Session, project: Project, repo_link: ProjectGithubRepo, data: dict[str, Any]) -> Commit:
    commit = db.query(Commit).filter(Commit.project_id == project.id, Commit.sha == data["sha"]).first()
    if commit is None:
        commit = Commit(project_id=project.id, sha=data["sha"])
    for key, value in data.items():
        setattr(commit, key, value)
    commit.repo_link_id = repo_link.id
    db.add(commit)
    return commit


def sync_repo(db: Session, project: Project, repo_link: ProjectGithubRepo, client: GithubClient, since: datetime) -> tuple[int, int]:
    pr_count = 0
    for pr in client.list_pulls(repo_link.full_name, since):
        if pr.get("number") is None:
            continue
        upsert_pull_request(db, project, repo_link, map_pull_request(pr, project.jira_project_key))
        pr_count += 1

    commit_count = 0
    for item in client.list_commits(repo_link.full_name, repo_link.default_branch, since):
        if not item.get("sha"):
            continue
        upsert_commit(db, project, repo_link, map_commit(item, project.jira_project_key))
        commit_count += 1

    repo_link.last_synced_at = datetime.now(UTC)
    db.add(repo_link)
    return pr_count, commit_count


def sync_project_github(db: Session, project: Project) -> GithubSyncResult:
    result = GithubSyncResult(project_id=project.id)
    since = datetime.now(UTC) - timedelta(days=SYNC_LOOKBACK_DAYS)
    links = (
        db.query(ProjectGithubRepo)
        .filter(ProjectGithubRepo.project_id == project.id)
        .order_by(ProjectGithubRepo.full_name)
        .all()
    )
    clients: dict[int, GithubClient] = {}
    try:
        for link in links:
            installation = link.installation
            if installation.suspended_at is not None:
                result.errors.append(GithubSyncError(repo=link.full_name, message="GitHub installation is suspended"))
                continue
            try:
                client = clients.get(installation.installation_id)
                if client is None:
                    client = GithubClient.for_installation(installation.installation_id)
                    clients[installation.installation_id] = client
                with db.begin_nested():
                    prs, commits = sync_repo(db, project, link, client, since)
                result.repos += 1
                result.pull_requests += prs
                result.commits += commits
            except GithubAPIError as exc:
                logger.warning("GitHub sync failed for %s: %s", link.full_name, exc)
                result.errors.append(GithubSyncError(repo=link.full_name, message=str(exc)))
    finally:
        for client in clients.values():
            client.close()

    db.commit()
    return result
