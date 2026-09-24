from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.jira.mappers import (
    adf_to_text,
    extract_epic_key,
    extract_parent_key,
    extract_sprint_ids,
    map_epic_or_story_status,
    map_story_status,
    map_task_priority,
    map_task_status,
    parse_jira_datetime,
)
from app.models.enums import IntegrationSource, TaskStatus
from app.models.epic import Epic
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.task import Task
from app.models.team_member import TeamMember


def ensure_assignee(
    db: Session,
    project: Project,
    fields: dict[str, Any],
    members_by_account: dict[str, TeamMember],
) -> uuid.UUID | None:
    assignee = fields.get("assignee") or {}
    account_id = assignee.get("accountId")
    if not account_id:
        return None
    member = members_by_account.get(account_id)
    if member:
        return member.id
    member = TeamMember(
        project_id=project.id,
        display_name=assignee.get("displayName") or account_id,
        email=assignee.get("emailAddress"),
        jira_account_id=account_id,
        is_active=True,
    )
    db.add(member)
    db.flush()
    members_by_account[account_id] = member
    return member.id


def story_points(fields: dict[str, Any], story_points_field: str | None) -> int | None:
    if not story_points_field:
        return None
    value = fields.get(story_points_field)
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def resolve_sprint_id(fields: dict[str, Any], sprints_by_jira_id: dict[str, Sprint]) -> uuid.UUID | None:
    for sprint_id in reversed(extract_sprint_ids(fields)):
        sprint = sprints_by_jira_id.get(sprint_id)
        if sprint:
            return sprint.id
    return None


def resolve_epic_id(fields: dict[str, Any], epics_by_key: dict[str, Epic]) -> uuid.UUID | None:
    candidates = []
    epic_key = extract_epic_key(fields)
    if epic_key:
        candidates.append(epic_key)
    parent_key = extract_parent_key(fields)
    if parent_key:
        candidates.append(parent_key)
    for key in candidates:
        epic = epics_by_key.get(key)
        if epic:
            return epic.id
    return None


def upsert_epic(
    db: Session,
    project: Project,
    issue: dict[str, Any],
    epics_by_key: dict[str, Epic],
) -> Epic:
    key = issue["key"]
    fields = issue.get("fields") or {}
    epic = epics_by_key.get(key)
    title = fields.get("summary") or key
    description = adf_to_text(fields.get("description"))
    status = map_epic_or_story_status(fields.get("status"))

    if epic is None:
        epic = Epic(
            project_id=project.id,
            external_key=key,
            source=IntegrationSource.jira,
            title=title,
            description=description,
            status=status,
        )
        db.add(epic)
        epics_by_key[key] = epic
    else:
        epic.title = title
        epic.description = description
        epic.status = status
    return epic


def upsert_story(
    db: Session,
    project: Project,
    issue: dict[str, Any],
    *,
    stories_by_key: dict[str, Story],
    epics_by_key: dict[str, Epic],
    members_by_account: dict[str, TeamMember],
    sprints_by_jira_id: dict[str, Sprint],
    story_points_field: str | None,
) -> Story:
    key = issue["key"]
    fields = issue.get("fields") or {}
    story = stories_by_key.get(key)
    title = fields.get("summary") or key
    description = adf_to_text(fields.get("description"))
    status = map_story_status(fields.get("status"))
    priority = map_task_priority(fields.get("priority"))
    points = story_points(fields, story_points_field)
    assignee_id = ensure_assignee(db, project, fields, members_by_account)
    epic_id = resolve_epic_id(fields, epics_by_key)
    sprint_id = resolve_sprint_id(fields, sprints_by_jira_id)

    if story is None:
        story = Story(
            project_id=project.id,
            external_key=key,
            source=IntegrationSource.jira,
            title=title,
            description=description,
            status=status,
            priority=priority,
            story_points=points,
            epic_id=epic_id,
            sprint_id=sprint_id,
            assignee_id=assignee_id,
        )
        db.add(story)
        stories_by_key[key] = story
    else:
        story.title = title
        story.description = description
        story.status = status
        story.priority = priority
        story.story_points = points
        story.epic_id = epic_id
        story.sprint_id = sprint_id
        story.assignee_id = assignee_id
    return story


def upsert_task(
    db: Session,
    project: Project,
    issue: dict[str, Any],
    *,
    tasks_by_key: dict[str, Task],
    epics_by_key: dict[str, Epic],
    stories_by_key: dict[str, Story],
    members_by_account: dict[str, TeamMember],
    sprints_by_jira_id: dict[str, Sprint],
    story_points_field: str | None,
) -> Task:
    key = issue["key"]
    fields = issue.get("fields") or {}
    task = tasks_by_key.get(key)
    title = fields.get("summary") or key
    description = adf_to_text(fields.get("description"))
    status = map_task_status(fields.get("status"))
    priority = map_task_priority(fields.get("priority"))
    points = story_points(fields, story_points_field)
    assignee_id = ensure_assignee(db, project, fields, members_by_account)
    epic_id = resolve_epic_id(fields, epics_by_key)
    sprint_id = resolve_sprint_id(fields, sprints_by_jira_id)

    story_id = None
    parent_key = extract_parent_key(fields)
    if parent_key and parent_key in stories_by_key:
        story_id = stories_by_key[parent_key].id
        if epic_id is None:
            epic_id = stories_by_key[parent_key].epic_id

    created_at = parse_jira_datetime(fields.get("created"))
    due_date = parse_jira_datetime(fields.get("duedate"))
    completed_at = parse_jira_datetime(fields.get("resolutiondate"))
    started_at = None
    if status in (TaskStatus.in_progress, TaskStatus.in_review, TaskStatus.blocked):
        started_at = parse_jira_datetime(fields.get("updated"))

    if task is None:
        task = Task(
            project_id=project.id,
            external_key=key,
            source=IntegrationSource.jira,
            title=title,
            description=description,
            status=status,
            priority=priority,
            story_points=points,
            assignee_id=assignee_id,
            sprint_id=sprint_id,
            epic_id=epic_id,
            story_id=story_id,
            due_date=due_date,
            completed_at=completed_at,
            started_at=started_at,
        )
        if created_at:
            task.created_at = created_at
        db.add(task)
        tasks_by_key[key] = task
    else:
        task.title = title
        task.description = description
        task.status = status
        task.priority = priority
        task.story_points = points
        task.assignee_id = assignee_id
        task.sprint_id = sprint_id
        task.epic_id = epic_id
        task.story_id = story_id
        task.due_date = due_date
        task.completed_at = completed_at
        if started_at and not task.started_at:
            task.started_at = started_at
    return task
