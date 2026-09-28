from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.github.client import GithubClient
from app.integrations.github.errors import GithubAPIError
from app.integrations.github.linking import apply_links, relink_project
from app.integrations.github.mappers import map_branch, map_commit, map_pull_request
from app.models.commit import Commit
from app.models.enums import IntegrationSource
from app.models.github_branch import GithubBranch
from app.models.project import Project
from app.models.project_github_repo import ProjectGithubRepo
from app.models.pull_request import PullRequest

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
    branches: int = 0
    errors: list[GithubSyncError] = field(default_factory=list)


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
    apply_links(db, project, pr)
    db.add(pr)
    return pr


def upsert_commit(db: Session, project: Project, repo_link: ProjectGithubRepo, data: dict[str, Any]) -> Commit:
    commit = db.query(Commit).filter(Commit.project_id == project.id, Commit.sha == data["sha"]).first()
    if commit is None:
        commit = Commit(project_id=project.id, sha=data["sha"])
    for key, value in data.items():
        setattr(commit, key, value)
    commit.repo_link_id = repo_link.id
    apply_links(db, project, commit)
    db.add(commit)
    return commit


def upsert_branch(db: Session, project: Project, repo_link: ProjectGithubRepo, data: dict[str, Any]) -> GithubBranch:
    branch = (
        db.query(GithubBranch)
        .filter(GithubBranch.repo_link_id == repo_link.id, GithubBranch.name == data["name"])
        .first()
    )
    if branch is None:
        branch = GithubBranch(project_id=project.id, repo_link_id=repo_link.id, name=data["name"])
    for key, value in data.items():
        setattr(branch, key, value)
    apply_links(db, project, branch)
    db.add(branch)
    return branch


def delete_branch(db: Session, repo_link: ProjectGithubRepo, name: str) -> None:
    (
        db.query(GithubBranch)
        .filter(GithubBranch.repo_link_id == repo_link.id, GithubBranch.name == name)
        .delete(synchronize_session=False)
    )


def sync_repo(
    db: Session, project: Project, repo_link: ProjectGithubRepo, client: GithubClient, since: datetime
) -> tuple[int, int, int]:
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

    seen_branches: set[str] = set()
    for item in client.list_branches(repo_link.full_name):
        name = item.get("name")
        if not name or name in seen_branches:
            continue
        seen_branches.add(name)
        head_sha = (item.get("commit") or {}).get("sha")
        upsert_branch(db, project, repo_link, map_branch(name, head_sha, project.jira_project_key))
    stale = db.query(GithubBranch).filter(GithubBranch.repo_link_id == repo_link.id)
    if seen_branches:
        stale = stale.filter(GithubBranch.name.notin_(seen_branches))
    stale.delete(synchronize_session=False)

    repo_link.last_synced_at = datetime.now(UTC)
    db.add(repo_link)
    return pr_count, commit_count, len(seen_branches)


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
                    prs, commits, branches = sync_repo(db, project, link, client, since)
                result.repos += 1
                result.pull_requests += prs
                result.commits += commits
                result.branches += branches
            except GithubAPIError as exc:
                logger.warning("GitHub sync failed for %s: %s", link.full_name, exc)
                result.errors.append(GithubSyncError(repo=link.full_name, message=str(exc)))
    finally:
        for client in clients.values():
            client.close()

    relink_project(db, project)
    db.commit()
    return result
