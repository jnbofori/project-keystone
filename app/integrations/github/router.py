from __future__ import annotations

import json
import logging
from typing import Annotated, Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from app.auth.security import get_current_user
from app.config import get_settings
from app.database import get_db
from app.integrations.github.app_auth import (
    build_install_url,
    create_install_state,
    exchange_user_code,
    forget_installation_token,
    parse_install_state,
)
from app.integrations.github.client import GithubClient
from app.integrations.github.errors import GithubAPIError
from app.integrations.github.sync import sync_project_github
from app.integrations.github.webhooks import handle_event, verify_signature
from app.models.commit import Commit
from app.models.github_branch import GithubBranch
from app.models.github_installation import GithubInstallation
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.project import ROLE_RANK, Project, ProjectMember, ProjectRole
from app.models.project_github_repo import ProjectGithubRepo
from app.models.pull_request import PullRequest
from app.models.user import User
from app.organizations.dependencies import require_org_member
from app.projects.dependencies import require_project_member
from app.schemas.github import (
    GithubActivityResponse,
    GithubBranchItem,
    GithubCommitItem,
    GithubInstallation as GithubInstallationSchema,
    GithubInstallStartResponse,
    GithubLinkedRepo,
    GithubPullRequestItem,
    GithubRepoLinkRequest,
    GithubRepoSummary,
    GithubSyncErrorItem,
    GithubSyncResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["github"])


def _require_github_configured() -> None:
    if not get_settings().github_app_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "GitHub App is not configured "
                "(set GITHUB_APP_ID, GITHUB_APP_SLUG, GITHUB_APP_PRIVATE_KEY, "
                "GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET)"
            ),
        )


def _github_http_error(exc: GithubAPIError) -> HTTPException:
    if exc.status_code in (401, 403):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub auth failed; reinstall the GitHub App",
        )
    if exc.status_code in (400, 404):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if exc.status_code == 503:
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def _frontend_redirect(status_value: str, **extra: str) -> RedirectResponse:
    base = get_settings().github_frontend_redirect
    params = {"status": status_value, **extra}
    if base.endswith("status=") or base.endswith("status"):
        url = f"{base}{status_value}"
        if extra:
            url = f"{url}&{urlencode(extra)}"
    elif "?" in base:
        url = f"{base}&{urlencode(params)}"
    else:
        url = f"{base}?{urlencode(params)}"
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


def _ensure_project_member(db: Session, project_id: UUID, user: User, min_role: ProjectRole) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a project member")
    if ROLE_RANK[membership.role] < ROLE_RANK[min_role]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return project


def _org_installations(db: Session, organization_id: UUID) -> list[GithubInstallation]:
    return (
        db.query(GithubInstallation)
        .filter(GithubInstallation.organization_id == organization_id)
        .order_by(GithubInstallation.account_login)
        .all()
    )


def _available_repos(db: Session, organization_id: UUID) -> list[tuple[GithubInstallation, dict[str, Any]]]:
    installations = [i for i in _org_installations(db, organization_id) if i.suspended_at is None]
    repos: list[tuple[GithubInstallation, dict[str, Any]]] = []
    failures: list[GithubAPIError] = []
    for installation in installations:
        try:
            with GithubClient.for_installation(installation.installation_id) as client:
                for repo in client.list_installation_repos():
                    if repo.get("id") is not None and repo.get("full_name"):
                        repos.append((installation, repo))
        except GithubAPIError as exc:
            logger.warning("Failed listing repos for GitHub installation %s: %s", installation.installation_id, exc)
            failures.append(exc)
    if installations and failures and len(failures) == len(installations):
        raise _github_http_error(failures[0])
    return repos


def _repo_summary(installation: GithubInstallation, repo: dict[str, Any]) -> GithubRepoSummary:
    return GithubRepoSummary(
        repo_id=int(repo["id"]),
        full_name=str(repo["full_name"]),
        private=bool(repo.get("private")),
        default_branch=repo.get("default_branch"),
        html_url=repo.get("html_url"),
        installation_id=installation.id,
        account_login=installation.account_login,
    )


def _linked_repos(db: Session, project_id: UUID) -> list[ProjectGithubRepo]:
    return (
        db.query(ProjectGithubRepo)
        .filter(ProjectGithubRepo.project_id == project_id)
        .order_by(ProjectGithubRepo.full_name)
        .all()
    )


@router.get("/organizations/me/github/install/start", response_model=GithubInstallStartResponse)
def start_github_install(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GithubInstallStartResponse:
    organization, _ = org_bundle
    _require_github_configured()
    state = create_install_state(organization.id, current_user.id)
    return GithubInstallStartResponse(install_url=build_install_url(state))


@router.get("/integrations/github/setup")
def github_setup_callback(
    db: Annotated[Session, Depends(get_db)],
    installation_id: Annotated[int | None, Query()] = None,
    setup_action: Annotated[str | None, Query()] = None,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    if installation_id is None:
        return _frontend_redirect("error", message="missing_installation_id")
    if not state:
        known = (
            db.query(GithubInstallation)
            .filter(GithubInstallation.installation_id == installation_id)
            .first()
        )
        if known and setup_action == "update":
            return _frontend_redirect("success", setup_action="update")
        return _frontend_redirect("error", message="missing_state")
    if not code:
        return _frontend_redirect("error", message="missing_code")

    _require_github_configured()
    try:
        organization_id, user_id = parse_install_state(state)
        user_token = exchange_user_code(code)
        with GithubClient.for_user(user_token) as user_client:
            visible_ids = {int(i["id"]) for i in user_client.user_installations() if i.get("id") is not None}
        if installation_id not in visible_ids:
            return _frontend_redirect("error", message="installation_not_accessible")

        with GithubClient.for_app() as app_client:
            details = app_client.get_installation(installation_id)
        account = details.get("account") or {}

        installation = (
            db.query(GithubInstallation)
            .filter(GithubInstallation.installation_id == installation_id)
            .first()
        )
        if installation is not None and installation.organization_id != organization_id:
            return _frontend_redirect("error", message="installation_linked_to_another_organization")
        if installation is None:
            installation = GithubInstallation(
                organization_id=organization_id,
                installation_id=installation_id,
                connected_by=user_id,
                account_login=str(account.get("login") or installation_id),
            )
        installation.account_login = str(account.get("login") or installation.account_login)
        installation.account_type = account.get("type")
        installation.account_avatar_url = account.get("avatar_url")
        installation.repository_selection = details.get("repository_selection")
        installation.suspended_at = None
        db.add(installation)
        db.commit()
        return _frontend_redirect("success", account=installation.account_login)
    except GithubAPIError as exc:
        db.rollback()
        logger.warning("GitHub setup callback failed: %s", exc)
        return _frontend_redirect("error", message=str(exc))
    except Exception:
        db.rollback()
        logger.exception("GitHub setup callback failed")
        return _frontend_redirect("error", message="install_failed")


@router.get("/organizations/me/github/installations", response_model=list[GithubInstallationSchema])
def list_github_installations(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.member)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> list[GithubInstallationSchema]:
    organization, _ = org_bundle
    return [GithubInstallationSchema.model_validate(i) for i in _org_installations(db, organization.id)]


@router.delete("/organizations/me/github/installations/{installation_row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_github_installation(
    installation_row_id: UUID,
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    organization, _ = org_bundle
    installation = db.get(GithubInstallation, installation_row_id)
    if installation is None or installation.organization_id != organization.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GitHub installation not found")

    if get_settings().github_app_configured:
        try:
            with GithubClient.for_app() as app_client:
                app_client.delete_installation(installation.installation_id)
        except GithubAPIError as exc:
            if exc.status_code != 404:
                logger.warning("Failed to uninstall GitHub App %s: %s", installation.installation_id, exc)
    forget_installation_token(installation.installation_id)
    db.delete(installation)
    db.commit()


@router.get("/integrations/github/repos", response_model=list[GithubRepoSummary])
def list_github_repos(
    project_id: Annotated[UUID, Query(description="Keystone project (uses its org GitHub installations)")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GithubRepoSummary]:
    project = _ensure_project_member(db, project_id, current_user, ProjectRole.member)
    _require_github_configured()
    repos = [_repo_summary(installation, repo) for installation, repo in _available_repos(db, project.organization_id)]
    return sorted(repos, key=lambda r: r.full_name.lower())


@router.get("/projects/{project_id}/github/repos", response_model=list[GithubLinkedRepo])
def get_linked_github_repos(
    project_membership: Annotated[
        tuple[Project, ProjectMember],
        Depends(require_project_member(ProjectRole.viewer)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> list[GithubLinkedRepo]:
    project, _ = project_membership
    return [GithubLinkedRepo.model_validate(link) for link in _linked_repos(db, project.id)]


@router.put("/projects/{project_id}/github/repos", response_model=list[GithubLinkedRepo])
def set_linked_github_repos(
    payload: GithubRepoLinkRequest,
    project_membership: Annotated[
        tuple[Project, ProjectMember],
        Depends(require_project_member(ProjectRole.admin)),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GithubLinkedRepo]:
    project, _ = project_membership
    wanted = set(payload.repo_ids)
    existing = {link.repo_id: link for link in _linked_repos(db, project.id)}

    for repo_id, link in existing.items():
        if repo_id not in wanted:
            db.delete(link)

    to_add = wanted - set(existing)
    if to_add:
        _require_github_configured()
        available = {int(repo["id"]): (installation, repo) for installation, repo in _available_repos(db, project.organization_id)}
        missing = sorted(to_add - set(available))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repositories not accessible to this organization's GitHub installations: {missing}",
            )
        for repo_id in to_add:
            installation, repo = available[repo_id]
            db.add(
                ProjectGithubRepo(
                    project_id=project.id,
                    installation_id=installation.id,
                    repo_id=repo_id,
                    full_name=str(repo["full_name"]),
                    default_branch=repo.get("default_branch"),
                    html_url=repo.get("html_url"),
                    linked_by=current_user.id,
                )
            )

    db.commit()
    return [GithubLinkedRepo.model_validate(link) for link in _linked_repos(db, project.id)]


@router.post("/projects/{project_id}/github/sync", response_model=GithubSyncResponse)
def sync_project_from_github(
    project_membership: Annotated[
        tuple[Project, ProjectMember],
        Depends(require_project_member(ProjectRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> GithubSyncResponse:
    project, _ = project_membership
    if not _linked_repos(db, project.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no linked GitHub repositories (PUT /projects/{id}/github/repos first)",
        )
    _require_github_configured()
    try:
        result = sync_project_github(db, project)
    except GithubAPIError as exc:
        db.rollback()
        raise _github_http_error(exc) from exc

    return GithubSyncResponse(
        project_id=result.project_id,
        repos=result.repos,
        pull_requests=result.pull_requests,
        commits=result.commits,
        branches=result.branches,
        errors=[GithubSyncErrorItem(repo=e.repo, message=e.message) for e in result.errors],
    )


@router.get("/projects/{project_id}/github/activity", response_model=GithubActivityResponse)
def get_github_activity(
    project_membership: Annotated[
        tuple[Project, ProjectMember],
        Depends(require_project_member(ProjectRole.viewer)),
    ],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GithubActivityResponse:
    project, _ = project_membership
    links = {link.id: link.full_name for link in _linked_repos(db, project.id)}

    pull_requests = (
        db.query(PullRequest)
        .options(joinedload(PullRequest.task), joinedload(PullRequest.story))
        .filter(PullRequest.project_id == project.id, PullRequest.repo_link_id.isnot(None))
        .order_by(func.coalesce(PullRequest.github_updated_at, PullRequest.opened_at).desc().nullslast())
        .limit(limit)
        .all()
    )
    commits = (
        db.query(Commit)
        .options(joinedload(Commit.task), joinedload(Commit.story))
        .filter(Commit.project_id == project.id, Commit.repo_link_id.isnot(None))
        .order_by(Commit.committed_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    branches = (
        db.query(GithubBranch)
        .options(joinedload(GithubBranch.task), joinedload(GithubBranch.story))
        .filter(GithubBranch.project_id == project.id)
        .order_by(GithubBranch.updated_at.desc())
        .limit(limit)
        .all()
    )

    return GithubActivityResponse(
        pull_requests=[
            GithubPullRequestItem(
                id=pr.id,
                repo_full_name=links.get(pr.repo_link_id),
                number=pr.number,
                title=pr.title,
                url=pr.url,
                status=pr.status,
                draft=pr.draft,
                author_login=pr.author_login,
                head_branch=pr.head_branch,
                base_branch=pr.base_branch,
                jira_keys=list(pr.jira_keys or []),
                task_key=pr.task.external_key if pr.task else None,
                story_key=pr.story.external_key if pr.story else None,
                opened_at=pr.opened_at,
                merged_at=pr.merged_at,
                closed_at=pr.closed_at,
                github_updated_at=pr.github_updated_at,
            )
            for pr in pull_requests
        ],
        commits=[
            GithubCommitItem(
                id=c.id,
                repo_full_name=links.get(c.repo_link_id),
                sha=c.sha,
                message=c.message,
                url=c.url,
                author_login=c.author_login,
                author_name=c.author_name,
                committed_at=c.committed_at,
                jira_keys=list(c.jira_keys or []),
                task_key=c.task.external_key if c.task else None,
                story_key=c.story.external_key if c.story else None,
            )
            for c in commits
        ],
        branches=[
            GithubBranchItem(
                id=b.id,
                repo_full_name=links.get(b.repo_link_id),
                name=b.name,
                head_sha=b.head_sha,
                jira_keys=list(b.jira_keys or []),
                task_key=b.task.external_key if b.task else None,
                story_key=b.story.external_key if b.story else None,
            )
            for b in branches
        ],
    )


@router.post("/integrations/github/webhooks", status_code=status.HTTP_202_ACCEPTED)
async def receive_github_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    secret = get_settings().github_webhook_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GitHub webhook secret not configured")
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    if not x_github_event or x_github_event == "ping":
        return {"status": "ignored"}

    try:
        payload = json.loads(body or b"{}")
    except ValueError:
        return {"status": "ignored"}
    if not isinstance(payload, dict):
        return {"status": "ignored"}

    try:
        result = await run_in_threadpool(handle_event, db, x_github_event, payload)
    except Exception:
        db.rollback()
        logger.exception("Failed handling GitHub webhook event %s", x_github_event)
        return {"status": "error"}
    return {"status": result}
