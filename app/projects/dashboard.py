from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Iterable
from pprint import pprint

from sqlalchemy.orm import Session

from app.models.enums import (
    EntityType,
    ProjectEventType,
    SprintStatus,
    StoryStatus,
    TaskStatus,
)
from app.models.epic import Epic
from app.models.project_event import ProjectEvent
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.task import Task, TaskDependency
from app.models.team_member import TeamMember
from app.schemas.dashboard import (
    DashboardAgingItem,
    DashboardAssigneeLoad,
    DashboardDueItem,
    DashboardEpicHealth,
    DashboardFlow,
    DashboardLoad,
    DashboardProgress,
    DashboardRiskIndicators,
    DashboardRisks,
    DashboardSprint,
    DashboardStatusCount,
    DashboardTime,
    DashboardVelocity,
    DeliveryRiskIndicator,
    DependencyRiskExample,
    DependencyRiskIndicator,
    ProjectDashboardResponse,
    ScopeRiskIndicator,
)

AGING_WIP_DAYS = 3.0
STALE_BLOCKED_DAYS = 2.0
PACE_TOLERANCE = 10.0
DEPENDENCY_DUE_SOON_DAYS = 2.0


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _now() -> datetime:
    return datetime.now(UTC)


def _points(value: int | float | None) -> float:
    return float(value) if value is not None else 0.0


def _story_done(status: StoryStatus) -> bool:
    return status == StoryStatus.done


def _task_done(status: TaskStatus) -> bool:
    return status == TaskStatus.done


def _task_open(status: TaskStatus) -> bool:
    return status not in (TaskStatus.done, TaskStatus.cancelled)


def _select_focus_sprint(db: Session, project_id: uuid.UUID) -> tuple[Sprint | None, bool]:
    active = (
        db.query(Sprint)
        .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.active)
        .order_by(Sprint.starts_at.desc().nullslast(), Sprint.created_at.desc())
        .first()
    )
    if active:
        return active, False

    completed = (
        db.query(Sprint)
        .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.completed)
        .order_by(Sprint.ends_at.desc().nullslast(), Sprint.completed_at.desc().nullslast())
        .first()
    )
    return completed, True if completed else False


def _sprint_stories(db: Session, project_id: uuid.UUID, sprint_id: uuid.UUID) -> list[Story]:
    return (
        db.query(Story)
        .filter(Story.project_id == project_id, Story.sprint_id == sprint_id)
        .all()
    )


def _sprint_tasks(db: Session, project_id: uuid.UUID, sprint_id: uuid.UUID) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.project_id == project_id, Task.sprint_id == sprint_id)
        .all()
    )


def _use_story_points(stories: Iterable[Story]) -> bool:
    return any(s.story_points is not None and s.story_points > 0 for s in stories)


def _completed_points_for_sprint(
    db: Session,
    project_id: uuid.UUID,
    sprint_id: uuid.UUID,
) -> float:
    stories = _sprint_stories(db, project_id, sprint_id)
    if _use_story_points(stories):
        return sum(_points(s.story_points) for s in stories if _story_done(s.status))
    tasks = _sprint_tasks(db, project_id, sprint_id)
    return sum(_points(t.story_points) for t in tasks if _task_done(t.status))


def _compute_progress(stories: list[Story], tasks: list[Task]) -> DashboardProgress:
    uses_points = _use_story_points(stories)
    if uses_points:
        total_points = sum(_points(s.story_points) for s in stories if s.status != StoryStatus.cancelled)
        completed_points = sum(
            _points(s.story_points) for s in stories if _story_done(s.status)
        )
        total_count = sum(1 for s in stories if s.status != StoryStatus.cancelled)
        completed_count = sum(1 for s in stories if _story_done(s.status))
    else:
        openish = [t for t in tasks if t.status != TaskStatus.cancelled]
        total_points = sum(_points(t.story_points) for t in openish)
        completed_points = sum(_points(t.story_points) for t in tasks if _task_done(t.status))
        total_count = len(openish)
        completed_count = sum(1 for t in tasks if _task_done(t.status))
        uses_points = total_points > 0

    percent: float | None = None
    if uses_points and total_points > 0:
        percent = round(100.0 * completed_points / total_points, 1)
    elif total_count > 0:
        percent = round(100.0 * completed_count / total_count, 1)

    return DashboardProgress(
        percent=percent,
        completed_points=round(completed_points, 1),
        total_points=round(total_points, 1),
        completed_count=completed_count,
        total_count=total_count,
        uses_points=uses_points,
    )


def _compute_time(sprint: Sprint) -> DashboardTime:
    now = _now()
    starts = _aware(sprint.starts_at)
    ends = _aware(sprint.ends_at)
    elapsed: float | None = None
    days_remaining: float | None = None

    if starts and ends and ends > starts:
        total = (ends - starts).total_seconds()
        elapsed_sec = min(max((now - starts).total_seconds(), 0.0), total)
        elapsed = round(100.0 * elapsed_sec / total, 1)
        days_remaining = max((ends - now).total_seconds() / 86400.0, 0.0)
        days_remaining = round(days_remaining, 1)
    elif ends:
        days_remaining = max((ends - now).total_seconds() / 86400.0, 0.0)
        days_remaining = round(days_remaining, 1)

    return DashboardTime(elapsed_percent=elapsed, days_remaining=days_remaining)


def _compute_velocity(
    db: Session,
    project_id: uuid.UUID,
    focus: Sprint | None,
    progress: DashboardProgress,
    time_info: DashboardTime,
) -> DashboardVelocity:
    completed = (
        db.query(Sprint)
        .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.completed)
        .order_by(Sprint.ends_at.desc().nullslast(), Sprint.completed_at.desc().nullslast())
        .limit(5)
        .all()
    )
    # Exclude focus sprint if it is still active (not completed)
    points_list: list[float] = []
    for sprint in completed:
        if focus and sprint.id == focus.id and focus.status != SprintStatus.completed:
            continue
        points_list.append(_completed_points_for_sprint(db, project_id, sprint.id))

    last = points_list[0] if points_list else None
    avg = round(sum(points_list[:3]) / len(points_list[:3]), 1) if points_list else None

    forecast: float | None = None
    if avg is not None and time_info.elapsed_percent is not None and time_info.elapsed_percent > 0:
        # Project current pace to full sprint: completed so far / elapsed fraction
        if progress.uses_points:
            forecast = round(progress.completed_points / (time_info.elapsed_percent / 100.0), 1)
        else:
            forecast = avg
    elif avg is not None:
        forecast = avg

    return DashboardVelocity(
        last_sprint_points=last,
        avg_3_sprint=avg,
        forecast_current=forecast,
    )


def _scope_added_points(
    db: Session,
    project_id: uuid.UUID,
    sprint: Sprint,
    stories: list[Story],
    tasks: list[Task],
) -> float:
    starts = _aware(sprint.starts_at)
    if not starts:
        return 0.0

    story_ids = {s.id for s in stories}
    task_ids = {t.id for t in tasks}
    story_by_id = {s.id: s for s in stories}
    task_by_id = {t.id: t for t in tasks}

    events = (
        db.query(ProjectEvent)
        .filter(
            ProjectEvent.project_id == project_id,
            ProjectEvent.timestamp >= starts,
            ProjectEvent.type.in_(
                [
                    ProjectEventType.ScopeChanged,
                    ProjectEventType.StoryCreated,
                    ProjectEventType.TaskCreated,
                ]
            ),
        )
        .all()
    )

    counted: set[uuid.UUID] = set()
    total = 0.0
    for event in events:
        if event.entity_id is None:
            continue
        if event.entity_type == EntityType.story and event.entity_id in story_ids:
            if event.entity_id in counted:
                continue
            counted.add(event.entity_id)
            total += _points(story_by_id[event.entity_id].story_points)
        elif event.entity_type == EntityType.task and event.entity_id in task_ids:
            # Only count task points when stories don't carry points
            if _use_story_points(stories):
                continue
            if event.entity_id in counted:
                continue
            counted.add(event.entity_id)
            total += _points(task_by_id[event.entity_id].story_points)
    return round(total, 1)


def _compute_risks(
    db: Session,
    project_id: uuid.UUID,
    sprint: Sprint,
    stories: list[Story],
    tasks: list[Task],
    progress: DashboardProgress,
    time_info: DashboardTime,
    velocity: DashboardVelocity,
) -> DashboardRisks:
    now = _now()
    starts = _aware(sprint.starts_at)
    ends = _aware(sprint.ends_at) or now

    # Blocked = TaskStatus.blocked, or Jira Flagged/Impediment on tasks or open stories
    blocked_items: list[Task | Story] = [
        t for t in tasks if t.status == TaskStatus.blocked or t.is_flagged
    ]
    blocked_items.extend(
        s
        for s in stories
        if s.is_flagged and s.status not in (StoryStatus.done, StoryStatus.cancelled)
    )
    stale_cutoff = now - timedelta(days=STALE_BLOCKED_DAYS)
    stale_blocked = sum(
        1 for item in blocked_items if _aware(item.updated_at) and _aware(item.updated_at) <= stale_cutoff
    )

    window_start = starts or (_aware(sprint.created_at) or now)
    # rate at which closed tasks are being reopened
    reopened = (
        db.query(ProjectEvent)
        .filter(
            ProjectEvent.project_id == project_id,
            ProjectEvent.type == ProjectEventType.TaskReopened,
            ProjectEvent.timestamp >= window_start,
            ProjectEvent.timestamp <= ends,
        )
        .count()
    )
    completed_events = (
        db.query(ProjectEvent)
        .filter(
            ProjectEvent.project_id == project_id,
            ProjectEvent.type == ProjectEventType.TaskCompleted,
            ProjectEvent.timestamp >= window_start,
            ProjectEvent.timestamp <= ends,
        )
        .count()
    )
    reopen_rate = round(reopened / completed_events, 2) if completed_events > 0 else None

    # the difference between the % of work completed and the & of sprint time elapsed
    # if the gap is greater than the tolerance, the sprint is ahead of schedule
    pace_gap: float | None = None
    pace_label: str | None = None
    if progress.percent is not None and time_info.elapsed_percent is not None:
        pace_gap = round(progress.percent - time_info.elapsed_percent, 1)
        if pace_gap >= PACE_TOLERANCE:
            pace_label = "Ahead"
        elif pace_gap <= -PACE_TOLERANCE:
            pace_label = "Behind"
        else:
            pace_label = "On track"

    remaining_points = max(progress.total_points - progress.completed_points, 0.0)
    remaining_fraction = None
    if time_info.elapsed_percent is not None:
        remaining_fraction = max(1.0 - time_info.elapsed_percent / 100.0, 0.0)

    carryover = False
    if (
        velocity.avg_3_sprint is not None
        and remaining_fraction is not None
        and progress.uses_points
        and remaining_fraction > 0
    ):
        expected_remaining_capacity = velocity.avg_3_sprint * remaining_fraction
        carryover = remaining_points > expected_remaining_capacity * 1.1
    elif pace_label == "Behind" and remaining_points > 0:
        carryover = True

    return DashboardRisks(
        blocked_count=len(blocked_items),
        stale_blocked_count=stale_blocked,
        scope_added_points=_scope_added_points(db, project_id, sprint, stories, tasks),
        reopened_count=reopened,
        reopen_rate=reopen_rate,
        pace_gap=pace_gap,
        carryover_likely=carryover,
        pace_label=pace_label,
    )


def _delivery_level(ratio: float | None) -> str | None:
    if ratio is None:
        return None
    if ratio <= 1.0:
        return "low"
    if ratio <= 1.25:
        return "medium"
    return "high"


def _scope_level(growth_percent: float | None) -> str | None:
    if growth_percent is None:
        return None
    if growth_percent < 10.0:
        return "low"
    if growth_percent < 25.0:
        return "medium"
    return "high"


def _compute_delivery_indicator(
    progress: DashboardProgress,
    time_info: DashboardTime,
    velocity: DashboardVelocity,
) -> DeliveryRiskIndicator:
    remaining_points = round(max(progress.total_points - progress.completed_points, 0.0), 1)
    historical = velocity.avg_3_sprint if velocity.avg_3_sprint is not None else velocity.last_sprint_points

    required: float | None = None
    ratio: float | None = None
    if time_info.elapsed_percent is not None:
        remaining_fraction = max(1.0 - time_info.elapsed_percent / 100.0, 0.01)
        required = round(remaining_points / remaining_fraction, 1)
        if historical is not None and historical > 0:
            ratio = round(required / historical, 2)

    return DeliveryRiskIndicator(
        level=_delivery_level(ratio),
        historical_velocity=historical,
        required_velocity=required,
        velocity_ratio=ratio,
        remaining_points=remaining_points,
    )


def _compute_scope_indicator(
    progress: DashboardProgress,
    scope_added_points: float,
) -> ScopeRiskIndicator:
    current = progress.total_points
    baseline = max(current - scope_added_points, 0.0)
    growth: float | None = None
    if baseline > 0:
        growth = round((current - baseline) / baseline * 100.0, 1)

    return ScopeRiskIndicator(
        level=_scope_level(growth),
        baseline_points=round(baseline, 1),
        current_points=round(current, 1),
        scope_added_points=scope_added_points,
        scope_growth_percent=growth,
    )


def _dependency_upstream_at_risk(
    depends_on: Task,
    stories_by_id: dict[uuid.UUID, Story],
) -> bool:
    if depends_on.status == TaskStatus.blocked or depends_on.is_flagged:
        return True
    if depends_on.story_id:
        story = stories_by_id.get(depends_on.story_id)
        if story is not None and story.is_flagged and story.status not in (
            StoryStatus.done,
            StoryStatus.cancelled,
        ):
            return True
    return False


def _compute_dependency_indicator(
    db: Session,
    project_id: uuid.UUID,
    tasks: list[Task],
    stories: list[Story],
) -> DependencyRiskIndicator:
    any_deps = (
        db.query(TaskDependency.id)
        .join(Task, Task.id == TaskDependency.task_id)
        .filter(Task.project_id == project_id)
        .first()
    )
    if any_deps is None:
        return DependencyRiskIndicator(
            level=None,
            at_risk_count=0,
            open_dependency_count=0,
            unavailable_reason="No dependency links synced",
        )

    open_tasks = [t for t in tasks if _task_open(t.status)]
    if not open_tasks:
        return DependencyRiskIndicator(level="low", at_risk_count=0, open_dependency_count=0)

    open_ids = [t.id for t in open_tasks]
    deps = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id.in_(open_ids))
        .all()
    )
    if not deps:
        return DependencyRiskIndicator(level="low", at_risk_count=0, open_dependency_count=0)

    tasks_by_id = {t.id: t for t in db.query(Task).filter(Task.project_id == project_id).all()}
    stories_by_id = {s.id: s for s in stories}
    # Also load parent stories for dependency tasks that may be outside sprint
    missing_story_ids = {
        tasks_by_id[d.depends_on_task_id].story_id
        for d in deps
        if d.depends_on_task_id in tasks_by_id and tasks_by_id[d.depends_on_task_id].story_id
    } - set(stories_by_id)
    if missing_story_ids:
        for story in db.query(Story).filter(Story.id.in_(missing_story_ids)).all():
            stories_by_id[story.id] = story

    now = _now()
    due_cutoff = now + timedelta(days=DEPENDENCY_DUE_SOON_DAYS)
    open_dependency_count = 0
    at_risk_count = 0
    examples: list[DependencyRiskExample] = []
    seen_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()

    for dep in deps:
        task = tasks_by_id.get(dep.task_id)
        depends_on = tasks_by_id.get(dep.depends_on_task_id)
        if task is None or depends_on is None:
            continue
        if not _task_open(depends_on.status):
            continue
        open_dependency_count += 1

        pair = (dep.task_id, dep.depends_on_task_id)
        reason: str | None = None
        if _dependency_upstream_at_risk(depends_on, stories_by_id):
            reason = "depends on blocked or flagged work"
        else:
            due = _aware(task.due_date)
            if due is not None and due <= due_cutoff:
                reason = "due within 2 days while dependency still open"

        if reason is None:
            continue
        at_risk_count += 1
        if pair not in seen_pairs and len(examples) < 5:
            seen_pairs.add(pair)
            examples.append(
                DependencyRiskExample(
                    task=task.title,
                    blocked_by=depends_on.title,
                    reason=reason,
                )
            )

    if at_risk_count > 0:
        level = "high"
    elif open_dependency_count > 0:
        level = "medium"
    else:
        level = "low"

    return DependencyRiskIndicator(
        level=level,
        at_risk_count=at_risk_count,
        open_dependency_count=open_dependency_count,
        examples=examples,
    )


def _compute_risk_indicators(
    db: Session,
    project_id: uuid.UUID,
    stories: list[Story],
    tasks: list[Task],
    progress: DashboardProgress,
    time_info: DashboardTime,
    velocity: DashboardVelocity,
    risks: DashboardRisks,
) -> DashboardRiskIndicators:
    return DashboardRiskIndicators(
        delivery=_compute_delivery_indicator(progress, time_info, velocity),
        scope=_compute_scope_indicator(progress, risks.scope_added_points),
        dependency=_compute_dependency_indicator(db, project_id, tasks, stories),
    )


def _compute_flow(tasks: list[Task], sprint: Sprint) -> DashboardFlow:
    now = _now()
    status_counts: dict[str, int] = defaultdict(int)
    for task in tasks:
        if task.status == TaskStatus.cancelled:
            continue
        status_counts[task.status.value] += 1

    by_status = [
        DashboardStatusCount(status=status, count=count)
        for status, count in sorted(status_counts.items(), key=lambda x: (-x[1], x[0]))
    ]

    aging: list[DashboardAgingItem] = []
    aging_statuses = {TaskStatus.in_progress, TaskStatus.in_review}
    for task in tasks:
        if task.status not in aging_statuses:
            continue
        updated = _aware(task.updated_at) or _aware(task.started_at) or _aware(task.created_at)
        if not updated:
            continue
        days = (now - updated).total_seconds() / 86400.0
        if days >= AGING_WIP_DAYS:
            aging.append(
                DashboardAgingItem(
                    id=task.id,
                    title=task.title,
                    days=round(days, 1),
                    status=task.status.value,
                    entity_type="task",
                )
            )
    aging.sort(key=lambda item: item.days, reverse=True)

    ends = _aware(sprint.ends_at) or now
    due_soon: list[DashboardDueItem] = []
    for task in tasks:
        if not _task_open(task.status) or not task.due_date:
            continue
        due = _aware(task.due_date)
        if due is None:
            continue
        if due <= ends or due < now:
            due_soon.append(
                DashboardDueItem(
                    id=task.id,
                    title=task.title,
                    due_date=due,
                    status=task.status.value,
                )
            )
    due_soon.sort(key=lambda item: item.due_date)

    return DashboardFlow(
        by_status=by_status,
        aging_wip=aging[:5],
        due_soon=due_soon[:5],
    )


def _compute_load(stories: list[Story], tasks: list[Task], members: list[TeamMember]) -> DashboardLoad:
    members_by_id = {m.id: m for m in members}
    open_points: dict[uuid.UUID | None, float] = defaultdict(float)
    open_tasks: dict[uuid.UUID | None, int] = defaultdict(int)

    use_stories = _use_story_points(stories)
    if use_stories:
        for story in stories:
            if story.status in (StoryStatus.done, StoryStatus.cancelled):
                continue
            open_points[story.assignee_id] += _points(story.story_points)
            open_tasks[story.assignee_id] += 1
    else:
        for task in tasks:
            if not _task_open(task.status):
                continue
            open_points[task.assignee_id] += _points(task.story_points)
            open_tasks[task.assignee_id] += 1

    rows: list[DashboardAssigneeLoad] = []
    assignee_ids = set(open_points.keys()) | set(open_tasks.keys())
    for assignee_id in assignee_ids:
        member = members_by_id.get(assignee_id) if assignee_id else None
        name = member.display_name if member else "Unassigned"
        rows.append(
            DashboardAssigneeLoad(
                assignee_id=assignee_id,
                name=name,
                open_points=round(open_points[assignee_id], 1),
                open_tasks=open_tasks[assignee_id],
                capacity_points=member.capacity_points if member else None,
            )
        )
    rows.sort(key=lambda row: (-row.open_points, -row.open_tasks, row.name))
    return DashboardLoad(by_assignee=rows[:10])


def _compute_epic_health(db: Session, project_id: uuid.UUID, stories: list[Story]) -> list[DashboardEpicHealth]:
    epic_ids = {s.epic_id for s in stories if s.epic_id}
    if not epic_ids:
        return []
    epics = db.query(Epic).filter(Epic.project_id == project_id, Epic.id.in_(epic_ids)).all()
    by_epic: dict[uuid.UUID, list[Story]] = defaultdict(list)
    for story in stories:
        if story.epic_id:
            by_epic[story.epic_id].append(story)

    rows: list[DashboardEpicHealth] = []
    for epic in epics:
        kids = [s for s in by_epic.get(epic.id, []) if s.status != StoryStatus.cancelled]
        if not kids:
            continue
        done = sum(1 for s in kids if _story_done(s.status))
        total = len(kids)
        rows.append(
            DashboardEpicHealth(
                id=epic.id,
                title=epic.title,
                done_stories=done,
                total_stories=total,
                percent_done=round(100.0 * done / total, 1) if total else None,
            )
        )
    rows.sort(key=lambda row: (row.percent_done is None, row.percent_done or 0))
    return rows[:6]


def build_project_dashboard(db: Session, project_id: uuid.UUID) -> ProjectDashboardResponse:
    sprint, is_fallback = _select_focus_sprint(db, project_id)

    if sprint is None:
        return ProjectDashboardResponse(
            project_id=project_id,
            active_sprint=None,
            progress=DashboardProgress(),
            time=DashboardTime(),
            velocity=DashboardVelocity(),
            risks=DashboardRisks(),
            risk_indicators=DashboardRiskIndicators(),
            flow=DashboardFlow(),
            load=DashboardLoad(),
            epic_health=[],
            message="No sprints found. Link Jira and sync to populate delivery data.",
        )

    stories = _sprint_stories(db, project_id, sprint.id)
    tasks = _sprint_tasks(db, project_id, sprint.id)
    members = db.query(TeamMember).filter(TeamMember.project_id == project_id).all()

    progress = _compute_progress(stories, tasks)
    time_info = _compute_time(sprint)
    velocity = _compute_velocity(db, project_id, sprint, progress, time_info)
    risks = _compute_risks(db, project_id, sprint, stories, tasks, progress, time_info, velocity)
    risk_indicators = _compute_risk_indicators(
        db, project_id, stories, tasks, progress, time_info, velocity, risks
    )
    flow = _compute_flow(tasks, sprint)
    load = _compute_load(stories, tasks, members)
    epic_health = _compute_epic_health(db, project_id, stories)

    message = None
    if is_fallback:
        message = "No active sprint — showing the most recently completed sprint."
    elif not stories and not tasks:
        message = "Sprint has no linked stories or tasks yet. Run a Jira sync after linking."

    return ProjectDashboardResponse(
        project_id=project_id,
        active_sprint=DashboardSprint(
            id=sprint.id,
            name=sprint.name,
            status=sprint.status.value,
            starts_at=_aware(sprint.starts_at),
            ends_at=_aware(sprint.ends_at),
            is_fallback=is_fallback,
        ),
        progress=progress,
        time=time_info,
        velocity=velocity,
        risks=risks,
        risk_indicators=risk_indicators,
        flow=flow,
        load=load,
        epic_health=epic_health,
        message=message,
    )
