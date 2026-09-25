from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.jira.mappers import (
    adf_to_text,
    extract_blocked_by_keys,
    extract_epic_key,
    extract_parent_key,
    extract_sprint_ids,
    is_flagged_impediment,
    map_epic_or_story_status,
    map_story_status,
    map_task_priority,
    map_task_status,
    parse_jira_datetime,
)
from app.models.enums import EntityType, IntegrationSource, ProjectEventType, SprintStatus, TaskStatus
from app.models.epic import Epic
from app.models.project import Project
from app.models.project_event import ProjectEvent
from app.models.sprint import Sprint
from app.models.sprint_requirement_baseline import SprintRequirementBaseline
from app.models.story import Story
from app.models.task import Task, TaskDependency
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


def acceptance_criteria_text(
    fields: dict[str, Any],
    acceptance_criteria_field: str | None,
) -> str | None:
    if not acceptance_criteria_field:
        return None
    return adf_to_text(fields.get(acceptance_criteria_field))


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


def ensure_requirement_baseline(
    db: Session,
    *,
    sprint: Sprint | None,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    title: str,
    description: str | None,
    acceptance_criteria: str | None,
    story_points_value: int | None,
) -> None:
    """Freeze planning text the first time an issue is seen on an active sprint."""
    if sprint is None or sprint.status != SprintStatus.active or entity_id is None:
        return
    exists = (
        db.query(SprintRequirementBaseline.id)
        .filter(
            SprintRequirementBaseline.sprint_id == sprint.id,
            SprintRequirementBaseline.entity_type == entity_type,
            SprintRequirementBaseline.entity_id == entity_id,
        )
        .first()
    )
    if exists:
        return
    db.add(
        SprintRequirementBaseline(
            sprint_id=sprint.id,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            story_points=story_points_value,
        )
    )


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
    flagged_field: str | None = None,
    acceptance_criteria_field: str | None = None,
) -> Story:
    key = issue["key"]
    fields = issue.get("fields") or {}
    story = stories_by_key.get(key)
    title = fields.get("summary") or key
    description = adf_to_text(fields.get("description"))
    ac_text = acceptance_criteria_text(fields, acceptance_criteria_field)
    status = map_story_status(fields.get("status"))
    priority = map_task_priority(fields.get("priority"))
    points = story_points(fields, story_points_field)
    assignee_id = ensure_assignee(db, project, fields, members_by_account)
    epic_id = resolve_epic_id(fields, epics_by_key)
    sprint_id = resolve_sprint_id(fields, sprints_by_jira_id)
    flagged = is_flagged_impediment(fields, flagged_field)
    sprint = None
    if sprint_id:
        sprint = next((s for s in sprints_by_jira_id.values() if s.id == sprint_id), None)

    if story is None:
        story = Story(
            project_id=project.id,
            external_key=key,
            source=IntegrationSource.jira,
            title=title,
            description=description,
            acceptance_criteria=ac_text,
            status=status,
            priority=priority,
            story_points=points,
            is_flagged=flagged,
            epic_id=epic_id,
            sprint_id=sprint_id,
            assignee_id=assignee_id,
        )
        db.add(story)
        stories_by_key[key] = story
    else:
        story.title = title
        story.description = description
        story.acceptance_criteria = ac_text
        story.status = status
        story.priority = priority
        story.story_points = points
        story.is_flagged = flagged
        story.epic_id = epic_id
        story.sprint_id = sprint_id
        story.assignee_id = assignee_id

    db.flush()
    ensure_requirement_baseline(
        db,
        sprint=sprint,
        entity_type=EntityType.story,
        entity_id=story.id,
        title=title,
        description=description,
        acceptance_criteria=ac_text,
        story_points_value=points,
    )
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
    flagged_field: str | None = None,
    acceptance_criteria_field: str | None = None,
) -> Task:
    key = issue["key"]
    fields = issue.get("fields") or {}
    task = tasks_by_key.get(key)
    title = fields.get("summary") or key
    description = adf_to_text(fields.get("description"))
    ac_text = acceptance_criteria_text(fields, acceptance_criteria_field)
    status = map_task_status(fields.get("status"))
    priority = map_task_priority(fields.get("priority"))
    points = story_points(fields, story_points_field)
    assignee_id = ensure_assignee(db, project, fields, members_by_account)
    epic_id = resolve_epic_id(fields, epics_by_key)
    sprint_id = resolve_sprint_id(fields, sprints_by_jira_id)
    flagged = is_flagged_impediment(fields, flagged_field)
    sprint = None
    if sprint_id:
        sprint = next((s for s in sprints_by_jira_id.values() if s.id == sprint_id), None)

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
            acceptance_criteria=ac_text,
            status=status,
            priority=priority,
            story_points=points,
            is_flagged=flagged,
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
        task.acceptance_criteria = ac_text
        task.status = status
        task.priority = priority
        task.story_points = points
        task.is_flagged = flagged
        task.assignee_id = assignee_id
        task.sprint_id = sprint_id
        task.epic_id = epic_id
        task.story_id = story_id
        task.due_date = due_date
        task.completed_at = completed_at
        if started_at and not task.started_at:
            task.started_at = started_at

    db.flush()
    ensure_requirement_baseline(
        db,
        sprint=sprint,
        entity_type=EntityType.task,
        entity_id=task.id,
        title=title,
        description=description,
        acceptance_criteria=ac_text,
        story_points_value=points,
    )
    return task


def sync_task_dependencies(
    db: Session,
    task: Task,
    issue: dict[str, Any],
    tasks_by_key: dict[str, Task],
    *,
    project: Project | None = None,
) -> None:
    """Replace outgoing TaskDependency rows from Jira Blocks / is blocked by links."""
    db.flush()
    if task.id is None:
        return

    fields = issue.get("fields") or {}
    depends_on_keys = extract_blocked_by_keys(fields)

    old_deps = {
        row.depends_on_task_id
        for row in db.query(TaskDependency).filter(TaskDependency.task_id == task.id).all()
    }

    db.query(TaskDependency).filter(TaskDependency.task_id == task.id).delete(
        synchronize_session=False
    )

    seen: set[uuid.UUID] = set()
    new_dep_ids: list[uuid.UUID] = []
    for key in depends_on_keys:
        depends_on = tasks_by_key.get(key)
        if depends_on is None or depends_on.id is None:
            continue
        if depends_on.id == task.id or depends_on.id in seen:
            continue
        seen.add(depends_on.id)
        db.add(TaskDependency(task_id=task.id, depends_on_task_id=depends_on.id))
        if depends_on.id not in old_deps:
            new_dep_ids.append(depends_on.id)

    if not new_dep_ids or project is None:
        return

    sprint = None
    if task.sprint_id:
        sprint = db.query(Sprint).filter(Sprint.id == task.sprint_id).first()
    if sprint is None or sprint.status != SprintStatus.active:
        return
    starts = sprint.starts_at
    if starts is None:
        return
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if now < starts:
        return

    for depends_on_id in new_dep_ids:
        external_key = f"{task.external_key or task.id}:dep:{depends_on_id}"
        exists = (
            db.query(ProjectEvent.id)
            .filter(
                ProjectEvent.project_id == project.id,
                ProjectEvent.external_key == external_key,
            )
            .first()
        )
        if exists:
            continue
        db.add(
            ProjectEvent(
                project_id=project.id,
                type=ProjectEventType.DependencyAdded,
                source=IntegrationSource.jira,
                entity_type=EntityType.task,
                entity_id=task.id,
                external_key=external_key,
                external_entity_key=task.external_key,
                timestamp=now,
                metadata_={"depends_on_task_id": str(depends_on_id)},
            )
        )
