from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.config import JIRA_OAUTH_SCOPES, get_settings
from app.database import get_db
from app.integrations.jira.client import JiraClient
from app.integrations.jira.crypto import decrypt_token, encrypt_token
from app.integrations.jira.errors import JiraAPIError
from app.integrations.jira.oauth import (
    accessible_resources,
    build_authorize_url,
    create_oauth_state,
    exchange_code,
    parse_oauth_state,
    refresh_tokens,
    token_expiry,
)
from app.integrations.jira.sync import sync_jira_project
from app.integrations.jira.webhooks import (
    handle_issue_webhook,
    register_project_webhook,
    unregister_org_webhooks,
    unregister_project_webhook,
)
from app.models.jira_connection import JiraConnection
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.project import ROLE_RANK, Project, ProjectMember, ProjectRole
from app.models.user import User
from app.organizations.dependencies import require_org_member
from app.projects.dependencies import require_project_member
from app.schemas.jira import (
    JiraCloudSelectRequest,
    JiraCloudSite,
    JiraConnectionResponse,
    JiraLinkRequest,
    JiraLinkResponse,
    JiraOAuthStartResponse,
    JiraProjectSummary,
    JiraSyncErrorItem,
    JiraSyncResponse,
    JiraWebhookSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["jira"])


def _require_jira_oauth_configured() -> None:
    settings = get_settings()
    if not settings.jira_oauth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Jira OAuth is not configured "
                "(set JIRA_OAUTH_CLIENT_ID, JIRA_OAUTH_CLIENT_SECRET, "
                "JIRA_OAUTH_REDIRECT_URI, JIRA_TOKEN_ENCRYPTION_KEY)"
            ),
        )


def _get_connection(db: Session, organization_id: UUID) -> JiraConnection | None:
    return (
        db.query(JiraConnection)
        .filter(JiraConnection.organization_id == organization_id)
        .first()
    )


def _require_connection(db: Session, organization_id: UUID) -> JiraConnection:
    connection = _get_connection(db, organization_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization has no Jira OAuth connection (GET /organizations/me/jira/oauth/start)",
        )
    if not connection.cloud_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jira site not selected (PUT /organizations/me/jira/cloud)",
        )
    return connection


def _client_for_org(db: Session, organization_id: UUID) -> JiraClient:
    connection = _require_connection(db, organization_id)
    return JiraClient.from_connection(db, connection, get_settings())


def _frontend_redirect(status_value: str, **extra: str) -> RedirectResponse:
    settings = get_settings()
    base = settings.jira_oauth_frontend_redirect
    params = {"status": status_value, **extra}
    if base.endswith("status=") or base.endswith("status"):
        url = f"{base}{status_value}"
        rest = {k: v for k, v in extra.items()}
        if rest:
            url = f"{url}&{urlencode(rest)}"
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


def _connection_response(connection: JiraConnection, available: list[JiraCloudSite] | None = None) -> JiraConnectionResponse:
    needs_site = connection.cloud_id is None
    return JiraConnectionResponse(
        connected=True,
        cloud_id=connection.cloud_id,
        site_url=connection.site_url,
        site_name=connection.site_name,
        token_expires_at=connection.token_expires_at,
        connected_by=connection.connected_by,
        needs_site_selection=needs_site,
        available_sites=available or [],
    )


@router.get("/organizations/me/jira/oauth/start", response_model=JiraOAuthStartResponse)
def start_jira_oauth(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JiraOAuthStartResponse:
    organization, _ = org_bundle
    _require_jira_oauth_configured()
    state = create_oauth_state(organization.id, current_user.id)
    return JiraOAuthStartResponse(authorize_url=build_authorize_url(state))


@router.get("/integrations/jira/oauth/callback")
def jira_oauth_callback(
    db: Annotated[Session, Depends(get_db)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    if error:
        return _frontend_redirect("error", message=error)
    if not code or not state:
        return _frontend_redirect("error", message="missing_code_or_state")

    _require_jira_oauth_configured()
    settings = get_settings()
    try:
        organization_id, user_id = parse_oauth_state(state, settings)
        token_data = exchange_code(code, settings)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            return _frontend_redirect("error", message="missing_refresh_token")

        resources = accessible_resources(access_token)
        cloud_id = None
        site_url = None
        site_name = None
        needs_site = "0"
        if len(resources) == 1:
            cloud_id = str(resources[0].get("id"))
            site_url = resources[0].get("url")
            site_name = resources[0].get("name")
        elif len(resources) > 1:
            needs_site = "1"

        connection = _get_connection(db, organization_id)
        if connection is None:
            connection = JiraConnection(
                organization_id=organization_id,
                connected_by=user_id,
                access_token_encrypted=encrypt_token(access_token, settings),
                refresh_token_encrypted=encrypt_token(refresh_token, settings),
                token_expires_at=token_expiry(token_data.get("expires_in")),
                scopes=token_data.get("scope") or JIRA_OAUTH_SCOPES,
                cloud_id=cloud_id,
                site_url=site_url,
                site_name=site_name,
            )
            db.add(connection)
        else:
            connection.access_token_encrypted = encrypt_token(access_token, settings)
            connection.refresh_token_encrypted = encrypt_token(refresh_token, settings)
            connection.token_expires_at = token_expiry(token_data.get("expires_in"))
            connection.scopes = token_data.get("scope") or connection.scopes or JIRA_OAUTH_SCOPES
            connection.connected_by = user_id
            connection.cloud_id = cloud_id
            connection.site_url = site_url
            connection.site_name = site_name
            db.add(connection)

        db.commit()
        return _frontend_redirect(
            "success",
            organization_id=str(organization_id),
            needs_site=needs_site,
        )
    except JiraAPIError as exc:
        db.rollback()
        return _frontend_redirect("error", message=str(exc))
    except Exception:
        db.rollback()
        return _frontend_redirect("error", message="oauth_failed")


@router.get("/organizations/me/jira/connection", response_model=JiraConnectionResponse)
def get_jira_connection(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> JiraConnectionResponse:
    organization, _ = org_bundle
    connection = _get_connection(db, organization.id)
    if connection is None:
        return JiraConnectionResponse(connected=False)

    available: list[JiraCloudSite] = []
    needs_site = connection.cloud_id is None
    if needs_site:
        try:
            client_settings = get_settings()
            access = decrypt_token(connection.access_token_encrypted, client_settings)
            expires_at = connection.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC) + timedelta(minutes=2):
                refresh = decrypt_token(connection.refresh_token_encrypted, client_settings)
                token_data = refresh_tokens(refresh, client_settings)
                access = token_data["access_token"]
                connection.access_token_encrypted = encrypt_token(access, client_settings)
                connection.refresh_token_encrypted = encrypt_token(
                    token_data.get("refresh_token") or refresh, client_settings
                )
                connection.token_expires_at = token_expiry(token_data.get("expires_in"))
                db.add(connection)
                db.commit()

            for resource in accessible_resources(access):
                rid = resource.get("id")
                if rid:
                    available.append(
                        JiraCloudSite(
                            cloud_id=str(rid),
                            site_url=resource.get("url"),
                            site_name=resource.get("name"),
                        )
                    )
        except JiraAPIError:
            available = []

    return _connection_response(connection, available)


@router.delete("/organizations/me/jira/connection", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_jira(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    organization, _ = org_bundle
    connection = _get_connection(db, organization.id)
    if connection:
        try:
            unregister_org_webhooks(db, organization.id, connection)
        except JiraAPIError:
            pass
        db.delete(connection)
        db.commit()


@router.put("/organizations/me/jira/cloud", response_model=JiraConnectionResponse)
def select_jira_cloud(
    payload: JiraCloudSelectRequest,
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> JiraConnectionResponse:
    organization, _ = org_bundle
    connection = _get_connection(db, organization.id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization has no Jira OAuth connection",
        )

    settings = get_settings()
    access = decrypt_token(connection.access_token_encrypted, settings)
    resources = accessible_resources(access)
    match = next((r for r in resources if str(r.get("id")) == payload.cloud_id), None)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cloud_id is not in accessible Atlassian sites for this connection",
        )

    connection.cloud_id = str(match["id"])
    connection.site_url = match.get("url")
    connection.site_name = match.get("name")
    db.add(connection)
    db.flush()

    linked = (
        db.query(Project)
        .filter(
            Project.organization_id == organization.id,
            Project.jira_project_key.isnot(None),
        )
        .all()
    )
    for project in linked:
        if not project.jira_project_key:
            continue
        try:
            register_project_webhook(db, project, connection, project.jira_project_key, settings)
        except JiraAPIError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to register Jira webhook for {project.jira_project_key}: {exc}",
            ) from exc

    db.commit()
    db.refresh(connection)
    return _connection_response(connection)


@router.get("/integrations/jira/projects", response_model=list[JiraProjectSummary])
def list_jira_projects(
    project_id: Annotated[UUID, Query(description="Keystone project (uses its org Jira connection)")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[JiraProjectSummary]:
    project = _ensure_project_member(db, project_id, current_user, ProjectRole.member)
    _require_jira_oauth_configured()
    try:
        with _client_for_org(db, project.organization_id) as client:
            projects = client.list_projects()
            db.commit()
    except JiraAPIError as exc:
        db.rollback()
        if exc.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Jira auth failed; reconnect OAuth",
            ) from exc
        if exc.status_code == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return [
        JiraProjectSummary(
            id=str(p.get("id")),
            key=str(p.get("key")),
            name=str(p.get("name") or p.get("key")),
            project_type_key=p.get("projectTypeKey"),
        )
        for p in projects
        if p.get("id") is not None and p.get("key")
    ]


@router.put("/projects/{project_id}/jira", response_model=JiraLinkResponse)
def link_jira_project(
    payload: JiraLinkRequest,
    project_membership: Annotated[
        tuple[Project, ProjectMember],
        Depends(require_project_member(ProjectRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> JiraLinkResponse:
    project, _ = project_membership
    key = (payload.jira_project_key or "").strip() or None

    if key is None:
        connection = _get_connection(db, project.organization_id)
        if connection:
            try:
                unregister_project_webhook(db, project, connection)
            except JiraAPIError:
                pass
        project.jira_project_key = None
        project.jira_project_id = None
        db.add(project)
        db.commit()
        db.refresh(project)
        return JiraLinkResponse(
            project_id=project.id,
            jira_project_key=None,
            jira_project_id=None,
        )

    _require_jira_oauth_configured()
    connection = _require_connection(db, project.organization_id)
    try:
        with _client_for_org(db, project.organization_id) as client:
            jira_project = client.get_project(key)
            db.flush()
    except JiraAPIError as exc:
        db.rollback()
        if exc.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Jira project '{key}' not found",
            ) from exc
        if exc.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Jira auth failed; reconnect OAuth",
            ) from exc
        if exc.status_code == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    conflict = (
        db.query(Project)
        .filter(
            Project.organization_id == project.organization_id,
            Project.jira_project_key == key,
            Project.id != project.id,
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Jira project '{key}' is already linked to another Keystone project in this organization",
        )

    project.jira_project_key = str(jira_project.get("key") or key)
    project.jira_project_id = str(jira_project.get("id") or "")
    db.add(project)
    db.flush()

    try:
        register_project_webhook(db, project, connection, project.jira_project_key)
    except JiraAPIError as exc:
        db.rollback()
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE if exc.status_code == 503 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to register Jira webhook: {exc}",
        ) from exc

    db.commit()
    db.refresh(project)
    return JiraLinkResponse(
        project_id=project.id,
        jira_project_key=project.jira_project_key,
        jira_project_id=project.jira_project_id,
    )


@router.post("/integrations/jira/webhooks/{project_id}")
def receive_jira_webhook(
    project_id: UUID,
    payload: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Query()] = None,
) -> dict[str, str]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not project.webhook_secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not registered")
    if not token or token != project.webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook token")

    try:
        handle_issue_webhook(db, project, payload)
    except Exception:
        db.rollback()
        logger.exception("Failed handling Jira webhook for project %s", project_id)
        return {"status": "error"}

    return {"status": "ok"}


@router.post("/projects/{project_id}/jira/sync", response_model=JiraSyncResponse)
def sync_project_from_jira(
    project_membership: Annotated[
        tuple[Project, ProjectMember],
        Depends(require_project_member(ProjectRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> JiraSyncResponse:
    project, _ = project_membership
    if not project.jira_project_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not linked to a Jira project (PUT /projects/{id}/jira first)",
        )

    _require_jira_oauth_configured()
    _require_connection(db, project.organization_id)
    try:
        result = sync_jira_project(db, project)
    except JiraAPIError as exc:
        db.rollback()
        if exc.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Jira project '{project.jira_project_key}' not found",
            ) from exc
        if exc.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Jira auth failed; reconnect OAuth",
            ) from exc
        if exc.status_code == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return JiraSyncResponse(
        project_id=result.project_id,
        jira_project_key=result.jira_project_key,
        team_members=result.team_members,
        sprints=result.sprints,
        epics=result.epics,
        stories=result.stories,
        tasks=result.tasks,
        events=result.events,
        errors=[
            JiraSyncErrorItem(entity=e.entity, key=e.key, message=e.message) for e in result.errors
        ],
    )


@router.get("/integrations/jira/webhooks", response_model=list[JiraWebhookSummary])
def list_jira_webhooks(
    project_id: Annotated[UUID, Query(description="Keystone project (uses its org Jira connection)")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[JiraWebhookSummary]:
    project = _ensure_project_member(db, project_id, current_user, ProjectRole.member)
    _require_jira_oauth_configured()
    try:
        with _client_for_org(db, project.organization_id) as client:
            webhooks = client.list_webhooks()
            db.commit()
    except JiraAPIError as exc:
        db.rollback()
        if exc.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Jira auth failed; reconnect OAuth",
            ) from exc
        if exc.status_code == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return [
        JiraWebhookSummary(
            id=str(w.get("id")),
            url=str(w.get("url")),
            events=[str(e) for e in (w.get("events") or [])],
            jql_filter=str(w.get("jqlFilter")) if w.get("jqlFilter") is not None else None,
            expiration_date=str(w.get("expirationDate")) if w.get("expirationDate") is not None else None,
        )
        for w in webhooks
        if w.get("id") is not None and w.get("url")
    ]
