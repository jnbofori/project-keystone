from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.integrations.jira.client import JiraClient
from app.integrations.jira.errors import JiraAPIError
from app.integrations.jira.mappers import classify_issue
from app.integrations.jira.upserts import upsert_epic, upsert_story, upsert_task
from app.models.enums import IntegrationSource
from app.models.epic import Epic
from app.models.jira_connection import JiraConnection
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.task import Task
from app.models.team_member import TeamMember

logger = logging.getLogger(__name__)

ISSUE_WEBHOOK_EVENTS = [
    "jira:issue_created",
    "jira:issue_updated",
    "jira:issue_deleted",
]


def _webhook_callback_url(project_id: UUID, secret: str, settings: Settings) -> str:
    base = (settings.jira_webhook_base_url or "").rstrip("/")
    if not base:
        raise JiraAPIError(
            "JIRA_WEBHOOK_BASE_URL is not configured",
            status_code=503,
        )
    query = urlencode({"token": secret})
    return f"{base}/integrations/jira/webhooks/{project_id}?{query}"


def _ensure_webhook_secret(project: Project) -> str:
    if project.webhook_secret:
        return project.webhook_secret
    project.webhook_secret = secrets.token_urlsafe(32)
    return project.webhook_secret


def _parse_expiration(payload: dict[str, Any]) -> datetime:
    raw = payload.get("expirationDate") or payload.get("expiryDate")
    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=UTC)
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
    return datetime.now(UTC) + timedelta(days=30)


def _extract_created_webhook_id(payload: dict[str, Any]) -> str | None:
    results = payload.get("webhookRegistrationResult") or []
    for item in results:
        if not isinstance(item, dict):
            continue
        errors = item.get("errors") or []
        if errors:
            raise JiraAPIError(
                f"Jira webhook registration failed: {errors}",
                status_code=502,
                body=item,
            )
        created = item.get("createdWebhookId")
        if created is not None:
            return str(created)
    return None


def unregister_project_webhook(
    db: Session,
    project: Project,
    connection: JiraConnection,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    webhook_id = project.webhook_id
    if not webhook_id:
        project.webhook_id = None
        project.webhook_expiration = None
        db.add(project)
        return

    if not connection.cloud_id:
        project.webhook_id = None
        project.webhook_expiration = None
        db.add(project)
        return

    try:
        with JiraClient.from_connection(db, connection, settings) as client:
            client.delete_webhooks([webhook_id])
    except JiraAPIError as exc:
        logger.warning("Failed to delete Jira webhook %s: %s", webhook_id, exc)

    project.webhook_id = None
    project.webhook_expiration = None
    db.add(project)


def register_project_webhook(
    db: Session,
    project: Project,
    connection: JiraConnection,
    jira_project_key: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if not connection.cloud_id:
        raise JiraAPIError("Jira site not selected", status_code=400)
    if not settings.jira_webhook_base_url.strip():
        raise JiraAPIError(
            "JIRA_WEBHOOK_BASE_URL is not configured",
            status_code=503,
        )

    if project.webhook_id:
        unregister_project_webhook(db, project, connection, settings)
        db.flush()

    secret = _ensure_webhook_secret(project)
    url = _webhook_callback_url(project.id, secret, settings)
    jql = f'project = "{jira_project_key}"'

    with JiraClient.from_connection(db, connection, settings) as client:
        payload = client.register_webhooks(
            url=url,
            events=ISSUE_WEBHOOK_EVENTS,
            jql_filter=jql,
        )

    webhook_id = _extract_created_webhook_id(payload or {})
    if not webhook_id:
        raise JiraAPIError("Jira webhook registration returned no webhook id", status_code=502, body=payload)

    project.webhook_id = webhook_id
    project.webhook_expiration = _parse_expiration(payload or {})
    project.webhook_secret = secret
    db.add(project)
    db.flush()


def unregister_org_webhooks(
    db: Session,
    organization_id: UUID,
    connection: JiraConnection,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    projects = (
        db.query(Project)
        .filter(Project.organization_id == organization_id, Project.webhook_id.isnot(None))
        .all()
    )
    for project in projects:
        try:
            unregister_project_webhook(db, project, connection, settings)
        except JiraAPIError as exc:
            logger.warning("Failed unregistering webhook for project %s: %s", project.id, exc)


def _load_lookup_maps(
    db: Session,
    project: Project,
) -> tuple[
    dict[str, Epic],
    dict[str, Story],
    dict[str, Task],
    dict[str, TeamMember],
    dict[str, Sprint],
]:
    epics_by_key = {
        e.external_key: e
        for e in db.query(Epic).filter(
            Epic.project_id == project.id,
            Epic.source == IntegrationSource.jira,
            Epic.external_key.isnot(None),
        )
        if e.external_key
    }
    stories_by_key = {
        s.external_key: s
        for s in db.query(Story).filter(
            Story.project_id == project.id,
            Story.source == IntegrationSource.jira,
            Story.external_key.isnot(None),
        )
        if s.external_key
    }
    tasks_by_key = {
        t.external_key: t
        for t in db.query(Task).filter(
            Task.project_id == project.id,
            Task.source == IntegrationSource.jira,
            Task.external_key.isnot(None),
        )
        if t.external_key
    }
    members_by_account = {
        m.jira_account_id: m
        for m in db.query(TeamMember).filter(
            TeamMember.project_id == project.id,
            TeamMember.jira_account_id.isnot(None),
        )
        if m.jira_account_id
    }
    sprints_by_jira_id = {
        s.external_key: s
        for s in db.query(Sprint).filter(
            Sprint.project_id == project.id,
            Sprint.source == IntegrationSource.jira,
            Sprint.external_key.isnot(None),
        )
        if s.external_key
    }
    return epics_by_key, stories_by_key, tasks_by_key, members_by_account, sprints_by_jira_id


def _issue_matches_project(issue_key: str, jira_project_key: str) -> bool:
    prefix, _, _rest = issue_key.partition("-")
    return prefix.upper() == jira_project_key.upper()


def handle_issue_webhook(
    db: Session,
    project: Project,
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    event = payload.get("webhookEvent") or payload.get("issue_event_type_name")
    issue = payload.get("issue") or {}
    issue_key = issue.get("key")
    if not isinstance(issue_key, str) or not issue_key:
        logger.info("Ignoring Jira webhook without issue key")
        return

    if not project.jira_project_key or not _issue_matches_project(issue_key, project.jira_project_key):
        logger.info("Ignoring Jira webhook for %s (project filter)", issue_key)
        return

    if event == "jira:issue_deleted":
        _delete_issue(db, project, issue_key)
        db.commit()
        return

    if event not in ("jira:issue_created", "jira:issue_updated"):
        logger.info("Ignoring unsupported Jira webhook event %s", event)
        return

    fields = issue.get("fields")
    if not isinstance(fields, dict) or not fields.get("issuetype"):
        logger.warning("Jira webhook for %s missing fields; skipping upsert", issue_key)
        return

    epics_by_key, stories_by_key, tasks_by_key, members_by_account, sprints_by_jira_id = _load_lookup_maps(
        db, project
    )
    story_points_field = settings.jira_story_points_field.strip() or None
    kind = classify_issue(issue)

    if kind == "epic":
        upsert_epic(db, project, issue, epics_by_key)
    elif kind == "story":
        upsert_story(
            db,
            project,
            issue,
            stories_by_key=stories_by_key,
            epics_by_key=epics_by_key,
            members_by_account=members_by_account,
            sprints_by_jira_id=sprints_by_jira_id,
            story_points_field=story_points_field,
        )
    else:
        upsert_task(
            db,
            project,
            issue,
            tasks_by_key=tasks_by_key,
            epics_by_key=epics_by_key,
            stories_by_key=stories_by_key,
            members_by_account=members_by_account,
            sprints_by_jira_id=sprints_by_jira_id,
            story_points_field=story_points_field,
        )
    db.commit()


def _delete_issue(db: Session, project: Project, issue_key: str) -> None:
    task = (
        db.query(Task)
        .filter(
            Task.project_id == project.id,
            Task.source == IntegrationSource.jira,
            Task.external_key == issue_key,
        )
        .first()
    )
    if task:
        db.delete(task)
        return

    story = (
        db.query(Story)
        .filter(
            Story.project_id == project.id,
            Story.source == IntegrationSource.jira,
            Story.external_key == issue_key,
        )
        .first()
    )
    if story:
        db.delete(story)
        return

    epic = (
        db.query(Epic)
        .filter(
            Epic.project_id == project.id,
            Epic.source == IntegrationSource.jira,
            Epic.external_key == issue_key,
        )
        .first()
    )
    if epic:
        db.delete(epic)
