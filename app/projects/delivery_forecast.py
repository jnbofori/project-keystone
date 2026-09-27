from __future__ import annotations

import math
import random
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enums import SprintStatus, StoryStatus, TaskStatus
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.task import Task
from app.schemas.delivery_forecast import ProjectDeliveryForecastResponse

TRIALS = 5000
MIN_SAMPLES = 3
MAX_SAMPLES = 8
HORIZON_DAYS = 365
METHOD_MONTE_CARLO = "monte_carlo_throughput"
METHOD_AVERAGE = "average_velocity"
DEFAULT_SPRINT_DAYS = 14


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _points(value: int | float | None) -> float:
    return float(value) if value is not None else 0.0


def _working_days_between(start: datetime, end: datetime) -> int:
    """Inclusive-ish working-day count between sprint start and end (Mon–Fri)."""
    start_d = start.date()
    end_d = end.date()
    if end_d < start_d:
        return 1
    days = 0
    cur = start_d
    while cur <= end_d:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return max(days, 1)


def _calendar_days_between(start: datetime, end: datetime) -> int:
    days = (end.date() - start.date()).days
    return max(days, 1)


def _project_remaining(db: Session, project_id: uuid.UUID) -> tuple[float, str]:
    stories = db.query(Story).filter(Story.project_id == project_id).all()
    open_stories = [s for s in stories if s.status not in (StoryStatus.done, StoryStatus.cancelled)]
    story_points_open = sum(_points(s.story_points) for s in open_stories)
    any_story_points = any(s.story_points is not None and s.story_points > 0 for s in stories)

    if any_story_points:
        return round(story_points_open, 1), "points"

    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    open_tasks = [t for t in tasks if t.status not in (TaskStatus.done, TaskStatus.cancelled)]
    task_points_open = sum(_points(t.story_points) for t in open_tasks)
    any_task_points = any(t.story_points is not None and t.story_points > 0 for t in tasks)

    if any_task_points:
        return round(task_points_open, 1), "points"

    if open_stories:
        return float(len(open_stories)), "items"
    return float(len(open_tasks)), "items"


def _completed_throughput_for_sprint(
    db: Session,
    project_id: uuid.UUID,
    sprint: Sprint,
    unit: str,
) -> float:
    stories = (
        db.query(Story)
        .filter(Story.project_id == project_id, Story.sprint_id == sprint.id)
        .all()
    )
    if unit == "items":
        done_stories = sum(1 for s in stories if s.status == StoryStatus.done)
        if done_stories or stories:
            # Prefer story count when stories exist on the sprint
            if stories:
                return float(done_stories)
        tasks = (
            db.query(Task)
            .filter(Task.project_id == project_id, Task.sprint_id == sprint.id)
            .all()
        )
        return float(sum(1 for t in tasks if t.status == TaskStatus.done))

    # points
    if any(s.story_points is not None and s.story_points > 0 for s in stories):
        return sum(_points(s.story_points) for s in stories if s.status == StoryStatus.done)
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id, Task.sprint_id == sprint.id)
        .all()
    )
    return sum(_points(t.story_points) for t in tasks if t.status == TaskStatus.done)


def _completed_sprints(db: Session, project_id: uuid.UUID) -> list[Sprint]:
    return (
        db.query(Sprint)
        .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.completed)
        .order_by(Sprint.ends_at.desc().nullslast(), Sprint.completed_at.desc().nullslast())
        .limit(MAX_SAMPLES)
        .all()
    )


def _historical_daily_rates(db: Session, project_id: uuid.UUID, unit: str) -> list[float]:
    rates: list[float] = []
    for sprint in _completed_sprints(db, project_id):
        starts = _aware(sprint.starts_at)
        ends = _aware(sprint.ends_at)
        if starts is None or ends is None:
            continue
        throughput = _completed_throughput_for_sprint(db, project_id, sprint, unit)
        length = _working_days_between(starts, ends)
        rate = throughput / length
        if rate > 0:
            rates.append(rate)
    return rates


def _sprint_throughputs(
    db: Session,
    project_id: uuid.UUID,
    unit: str,
) -> tuple[list[float], list[int]]:
    """Return (positive throughputs per sprint, calendar lengths for those sprints)."""
    throughputs: list[float] = []
    lengths: list[int] = []
    for sprint in _completed_sprints(db, project_id):
        throughput = _completed_throughput_for_sprint(db, project_id, sprint, unit)
        if throughput <= 0:
            continue
        throughputs.append(throughput)
        starts = _aware(sprint.starts_at)
        ends = _aware(sprint.ends_at)
        if starts is not None and ends is not None:
            lengths.append(_calendar_days_between(starts, ends))
    return throughputs, lengths


def _average_velocity_forecast(
    *,
    project_id: uuid.UUID,
    remaining: float,
    unit: str,
    throughputs: list[float],
    sprint_lengths: list[int],
) -> ProjectDeliveryForecastResponse:
    average_velocity = sum(throughputs) / len(throughputs)
    estimated_sprints = remaining / average_velocity
    likely_sprints = max(int(math.ceil(estimated_sprints)), 1)
    avg_sprint_days = (
        sum(sprint_lengths) / len(sprint_lengths) if sprint_lengths else float(DEFAULT_SPRINT_DAYS)
    )
    today = datetime.now(UTC).date()
    p50 = today + timedelta(days=int(round(likely_sprints * avg_sprint_days)))

    return ProjectDeliveryForecastResponse(
        project_id=project_id,
        remaining=remaining,
        unit=unit,
        samples_used=len(throughputs),
        trials=0,
        method=METHOD_AVERAGE,
        p50_date=p50,
        p85_date=None,
        p95_date=None,
        historical_rates=[],
        average_velocity=round(average_velocity, 1),
        estimated_sprints=round(estimated_sprints, 1),
        likely_sprints=likely_sprints,
    )


def _percentile_date(sorted_dates: list[date], pct: float) -> date | None:
    if not sorted_dates:
        return None
    if len(sorted_dates) == 1:
        return sorted_dates[0]
    # Nearest-rank style index
    idx = int(round((pct / 100.0) * (len(sorted_dates) - 1)))
    idx = max(0, min(idx, len(sorted_dates) - 1))
    return sorted_dates[idx]


def _run_monte_carlo(remaining: float, rates: list[float], trials: int = TRIALS) -> list[date]:
    rng = random.Random()
    today = datetime.now(UTC).date()
    finish_dates: list[date] = []

    for _ in range(trials):
        left = remaining
        day = today
        for _step in range(HORIZON_DAYS):
            if day.weekday() < 5:
                left -= rng.choice(rates)
                if left <= 0:
                    finish_dates.append(day)
                    break
            day += timedelta(days=1)
        # unfinished trials omitted from percentile pool
    return finish_dates


def build_project_delivery_forecast(
    db: Session,
    project_id: uuid.UUID,
) -> ProjectDeliveryForecastResponse:
    remaining, unit = _project_remaining(db, project_id)

    if remaining <= 0:
        return ProjectDeliveryForecastResponse(
            project_id=project_id,
            remaining=0,
            unit=unit,
            samples_used=0,
            trials=TRIALS,
            method=METHOD_MONTE_CARLO,
            already_complete=True,
        )

    rates = _historical_daily_rates(db, project_id, unit)
    if len(rates) < MIN_SAMPLES:
        throughputs, sprint_lengths = _sprint_throughputs(db, project_id, unit)
        if throughputs:
            return _average_velocity_forecast(
                project_id=project_id,
                remaining=remaining,
                unit=unit,
                throughputs=throughputs,
                sprint_lengths=sprint_lengths,
            )
        return ProjectDeliveryForecastResponse(
            project_id=project_id,
            remaining=remaining,
            unit=unit,
            samples_used=0,
            trials=TRIALS,
            method=METHOD_MONTE_CARLO,
            historical_rates=[],
            unavailable_reason=(
                f"Need at least {MIN_SAMPLES} completed sprints with throughput; "
                "found 0."
            ),
        )

    finish_dates = _run_monte_carlo(remaining, rates, TRIALS)
    finish_dates.sort()

    return ProjectDeliveryForecastResponse(
        project_id=project_id,
        remaining=remaining,
        unit=unit,
        samples_used=len(rates),
        trials=TRIALS,
        method=METHOD_MONTE_CARLO,
        p50_date=_percentile_date(finish_dates, 50),
        p85_date=_percentile_date(finish_dates, 85),
        p95_date=_percentile_date(finish_dates, 95),
        historical_rates=[round(r, 3) for r in rates],
    )
