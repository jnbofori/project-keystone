from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from pprint import pprint
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.integrations.jira.client import JiraClient
from app.integrations.jira.errors import JiraAPIError
from app.integrations.jira.mappers import (
    classify_issue,
    map_changelog_item,
    map_sprint_status,
    parse_jira_datetime,
)
from app.integrations.jira.upserts import (
    upsert_epic as _upsert_epic,
    upsert_story as _upsert_story,
    upsert_task as _upsert_task,
)
from app.models.enums import EntityType, IntegrationSource, ProjectEventType
from app.models.epic import Epic
from app.models.jira_connection import JiraConnection
from app.models.project import Project
from app.models.project_event import ProjectEvent
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.task import Task
from app.models.team_member import TeamMember

logger = logging.getLogger(__name__)


@dataclass
class SyncError:
    entity: str
    key: str | None
    message: str


@dataclass
class SyncResult:
    project_id: uuid.UUID
    jira_project_key: str
    team_members: int = 0
    sprints: int = 0
    epics: int = 0
    stories: int = 0
    tasks: int = 0
    events: int = 0
    errors: list[SyncError] = field(default_factory=list)


def sync_jira_project(
    db: Session,
    project: Project,
    settings: Settings | None = None,
) -> SyncResult:
    settings = settings or get_settings()
    if not project.jira_project_key:
        raise ValueError("Project is not linked to a Jira project key")

    connection = (
        db.query(JiraConnection)
        .filter(JiraConnection.organization_id == project.organization_id)
        .first()
    )
    if connection is None:
        raise ValueError(
            "Organization has no Jira OAuth connection "
            "(connect via /organizations/me/jira/oauth/start)"
        )

    result = SyncResult(project_id=project.id, jira_project_key=project.jira_project_key)

    with JiraClient.from_connection(db, connection, settings) as client:
        _sync_project_metadata(client, db, project, result)
        members_by_account = _sync_team_members(client, db, project, result)
        sprints_by_jira_id = _sync_sprints(client, db, project, result)
        story_points_field = client.resolve_story_points_field()
        sprint_field = client.resolve_sprint_field()
        flagged_field = client.resolve_flagged_field()
        epics_by_key, stories_by_key, tasks_by_key = _sync_issues(
            client,
            db,
            project,
            result,
            members_by_account=members_by_account,
            sprints_by_jira_id=sprints_by_jira_id,
            story_points_field=story_points_field,
            sprint_field=sprint_field,
            flagged_field=flagged_field,
        )
        _sync_events(
            client,
            db,
            project,
            result,
            members_by_account=members_by_account,
            epics_by_key=epics_by_key,
            stories_by_key=stories_by_key,
            tasks_by_key=tasks_by_key,
        )

    db.commit()
    return result


def _sync_project_metadata(
    client: JiraClient,
    db: Session,
    project: Project,
    result: SyncResult,
) -> None:
    try:
        jira_project = client.get_project(project.jira_project_key)
    except JiraAPIError as exc:
        result.errors.append(SyncError("project", project.jira_project_key, str(exc)))
        raise

    project.jira_project_id = str(jira_project.get("id") or project.jira_project_id or "")
    description = jira_project.get("description")
    if isinstance(description, str) and description.strip():
        project.description = description.strip()
    elif not project.description:
        project.description = None
    db.add(project)


def _sync_team_members(
    client: JiraClient,
    db: Session,
    project: Project,
    result: SyncResult,
) -> dict[str, TeamMember]:
    by_account: dict[str, TeamMember] = {
        m.jira_account_id: m
        for m in db.query(TeamMember).filter(
            TeamMember.project_id == project.id,
            TeamMember.jira_account_id.isnot(None),
        )
        if m.jira_account_id
    }

    try:
        role_urls = client.list_project_role_urls(project.jira_project_key)
    except JiraAPIError as exc:
        result.errors.append(SyncError("team_members", project.jira_project_key, str(exc)))
        return by_account

    seen: set[str] = set()
    for _role_name, role_url in role_urls.items():
        try:
            role = client.get_project_role(role_url)
        except JiraAPIError as exc:
            result.errors.append(SyncError("team_members", role_url, str(exc)))
            continue

        for actor in role.get("actors") or []:
            actor_user = actor.get("actorUser") or {}
            account_id = actor_user.get("accountId") or actor.get("accountId")
            if not account_id or account_id in seen:
                continue
            seen.add(account_id)

            display_name = (
                actor.get("displayName")
                or actor_user.get("displayName")
                or account_id
            )
            email = actor_user.get("emailAddress") or actor.get("emailAddress")

            member = by_account.get(account_id)
            if member is None:
                member = TeamMember(
                    project_id=project.id,
                    display_name=display_name,
                    email=email,
                    jira_account_id=account_id,
                    is_active=True,
                )
                db.add(member)
                by_account[account_id] = member
                result.team_members += 1
            else:
                member.display_name = display_name or member.display_name
                if email:
                    member.email = email
                member.is_active = True
                result.team_members += 1

    db.flush()
    return by_account


def _sync_sprints(
    client: JiraClient,
    db: Session,
    project: Project,
    result: SyncResult,
) -> dict[str, Sprint]:
    by_id: dict[str, Sprint] = {
        s.external_key: s
        for s in db.query(Sprint).filter(
            Sprint.project_id == project.id,
            Sprint.source == IntegrationSource.jira,
            Sprint.external_key.isnot(None),
        )
        if s.external_key
    }

    try:
        boards = client.list_boards(project.jira_project_key)
    except JiraAPIError as exc:
        result.errors.append(SyncError("sprints", project.jira_project_key, str(exc)))
        return by_id

    for board in boards:
        board_id = board.get("id")
        if board_id is None:
            continue
        try:
            sprints = client.list_board_sprints(board_id)
        except JiraAPIError as exc:
            result.errors.append(SyncError("sprints", str(board_id), str(exc)))
            continue

        for raw in sprints:
            sprint_id = raw.get("id")
            if sprint_id is None:
                continue
            external_key = str(sprint_id)
            sprint = by_id.get(external_key)
            name = raw.get("name") or f"Sprint {external_key}"
            status = map_sprint_status(raw.get("state"))
            starts_at = parse_jira_datetime(raw.get("startDate"))
            ends_at = parse_jira_datetime(raw.get("endDate"))
            completed_at = parse_jira_datetime(raw.get("completeDate"))

            if sprint is None:
                sprint = Sprint(
                    project_id=project.id,
                    external_key=external_key,
                    source=IntegrationSource.jira,
                    name=name,
                    goal=raw.get("goal"),
                    status=status,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    completed_at=completed_at,
                )
                db.add(sprint)
                by_id[external_key] = sprint
            else:
                sprint.name = name
                sprint.goal = raw.get("goal")
                sprint.status = status
                sprint.starts_at = starts_at
                sprint.ends_at = ends_at
                sprint.completed_at = completed_at
            result.sprints += 1

    db.flush()
    return by_id


def _sync_issues(
    client: JiraClient,
    db: Session,
    project: Project,
    result: SyncResult,
    *,
    members_by_account: dict[str, TeamMember],
    sprints_by_jira_id: dict[str, Sprint],
    story_points_field: str | None,
    sprint_field: str,
    flagged_field: str | None = None,
) -> tuple[dict[str, Epic], dict[str, Story], dict[str, Task]]:
    fields = [
        "summary",
        "description",
        "status",
        "priority",
        "assignee",
        "issuetype",
        "parent",
        "created",
        "updated",
        "duedate",
        "resolutiondate",
        "labels",
        "sprint",
    ]
    if story_points_field:
        fields.append(story_points_field)
    if sprint_field and sprint_field not in fields:
        fields.append(sprint_field)
    if flagged_field and flagged_field not in fields:
        fields.append(flagged_field)

    jql = f'project = "{project.jira_project_key}" ORDER BY created ASC'
    try:
        issues = client.search_issues(jql, fields=fields)
    except JiraAPIError as exc:
        result.errors.append(SyncError("issues", project.jira_project_key, str(exc)))
        return {}, {}, {}

    epics_by_key: dict[str, Epic] = {
        e.external_key: e
        for e in db.query(Epic).filter(
            Epic.project_id == project.id,
            Epic.source == IntegrationSource.jira,
            Epic.external_key.isnot(None),
        )
        if e.external_key
    }
    stories_by_key: dict[str, Story] = {
        s.external_key: s
        for s in db.query(Story).filter(
            Story.project_id == project.id,
            Story.source == IntegrationSource.jira,
            Story.external_key.isnot(None),
        )
        if s.external_key
    }
    tasks_by_key: dict[str, Task] = {
        t.external_key: t
        for t in db.query(Task).filter(
            Task.project_id == project.id,
            Task.source == IntegrationSource.jira,
            Task.external_key.isnot(None),
        )
        if t.external_key
    }

    # Pass 1: epics
    for issue in issues:
        if classify_issue(issue) != "epic":
            continue
        try:
            _upsert_epic(db, project, issue, epics_by_key)
            result.epics += 1
        except Exception as exc:  # noqa: BLE001
            key = issue.get("key")
            result.errors.append(SyncError("epic", key, str(exc)))
            logger.exception("Failed to upsert epic %s", key)
    db.flush()

    # Pass 2: stories
    for issue in issues:
        if classify_issue(issue) != "story":
            continue
        try:
            pprint(f"issue: {issue}")
            _upsert_story(
                db,
                project,
                issue,
                stories_by_key=stories_by_key,
                epics_by_key=epics_by_key,
                members_by_account=members_by_account,
                sprints_by_jira_id=sprints_by_jira_id,
                story_points_field=story_points_field,
                flagged_field=flagged_field,
            )
            result.stories += 1
        except Exception as exc:  # noqa: BLE001
            key = issue.get("key")
            result.errors.append(SyncError("story", key, str(exc)))
            logger.exception("Failed to upsert story %s", key)
    db.flush()

    # Pass 3: tasks / other
    for issue in issues:
        if classify_issue(issue) != "task":
            continue
        try:
            _upsert_task(
                db,
                project,
                issue,
                tasks_by_key=tasks_by_key,
                epics_by_key=epics_by_key,
                stories_by_key=stories_by_key,
                members_by_account=members_by_account,
                sprints_by_jira_id=sprints_by_jira_id,
                story_points_field=story_points_field,
                flagged_field=flagged_field,
            )
            result.tasks += 1
        except Exception as exc:  # noqa: BLE001
            key = issue.get("key")
            result.errors.append(SyncError("task", key, str(exc)))
            logger.exception("Failed to upsert task %s", key)
    db.flush()

    return epics_by_key, stories_by_key, tasks_by_key



def _sync_events(
    client: JiraClient,
    db: Session,
    project: Project,
    result: SyncResult,
    *,
    members_by_account: dict[str, TeamMember],
    epics_by_key: dict[str, Epic],
    stories_by_key: dict[str, Story],
    tasks_by_key: dict[str, Task],
) -> None:
    existing_keys = {
        e.external_key
        for e in db.query(ProjectEvent.external_key).filter(
            ProjectEvent.project_id == project.id,
            ProjectEvent.source == IntegrationSource.jira,
            ProjectEvent.external_key.isnot(None),
        )
        if e.external_key
    }

    all_issues: list[tuple[str, EntityType, uuid.UUID]] = []
    for key, epic in epics_by_key.items():
        all_issues.append((key, EntityType.epic, epic.id))
    for key, story in stories_by_key.items():
        all_issues.append((key, EntityType.story, story.id))
    for key, task in tasks_by_key.items():
        all_issues.append((key, EntityType.task, task.id))

    for issue_key, entity_type, entity_id in all_issues:
        try:
            histories = client.get_issue_changelog(issue_key)
        except JiraAPIError as exc:
            result.errors.append(SyncError("events", issue_key, str(exc)))
            continue

        # Synthetic created event
        created_key = f"{issue_key}:created"
        if created_key not in existing_keys:
            created_at = None
            if entity_type == EntityType.task:
                created_at = tasks_by_key[issue_key].created_at
            elif entity_type == EntityType.story:
                created_at = stories_by_key[issue_key].created_at
            elif entity_type == EntityType.epic:
                created_at = epics_by_key[issue_key].created_at
            if created_at:
                event_type = (
                    ProjectEventType.EpicCreated
                    if entity_type == EntityType.epic
                    else ProjectEventType.TaskCreated
                )
                if entity_type == EntityType.story:
                    event_type = ProjectEventType.StoryCreated
                db.add(
                    ProjectEvent(
                        project_id=project.id,
                        type=event_type,
                        source=IntegrationSource.jira,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        external_key=created_key,
                        external_entity_key=issue_key,
                        timestamp=created_at,
                        metadata_={"source": "jira_sync"},
                    )
                )
                existing_keys.add(created_key)
                result.events += 1

        for history in histories:
            history_id = history.get("id")
            timestamp = parse_jira_datetime(history.get("created"))
            if not timestamp or history_id is None:
                continue
            author = history.get("author") or {}
            actor_account = author.get("accountId")
            actor_id = None
            if actor_account and actor_account in members_by_account:
                actor_id = members_by_account[actor_account].id

            for item in history.get("items") or []:
                field = item.get("field") or ""
                event_type = map_changelog_item(field, item.get("fromString"), item.get("toString"))
                if event_type is None:
                    continue
                external_key = f"{issue_key}:{history_id}:{field}"
                if external_key in existing_keys:
                    continue
                db.add(
                    ProjectEvent(
                        project_id=project.id,
                        type=event_type,
                        source=IntegrationSource.jira,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        external_key=external_key,
                        external_entity_key=issue_key,
                        actor_team_member_id=actor_id,
                        timestamp=timestamp,
                        metadata_={
                            "field": field,
                            "from": item.get("fromString"),
                            "to": item.get("toString"),
                        },
                    )
                )
                existing_keys.add(external_key)
                result.events += 1

    db.flush()
