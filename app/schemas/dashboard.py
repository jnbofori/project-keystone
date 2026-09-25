from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DashboardSprint(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_fallback: bool = False


class DashboardProgress(BaseModel):
    percent: float | None = None
    completed_points: float = 0
    total_points: float = 0
    completed_count: int = 0
    total_count: int = 0
    uses_points: bool = False


class DashboardTime(BaseModel):
    elapsed_percent: float | None = None
    days_remaining: float | None = None


class DashboardVelocity(BaseModel):
    last_sprint_points: float | None = None
    avg_3_sprint: float | None = None
    forecast_current: float | None = None


class DashboardRisks(BaseModel):
    blocked_count: int = 0
    stale_blocked_count: int = 0
    scope_added_points: float = 0
    reopened_count: int = 0
    reopen_rate: float | None = None
    pace_gap: float | None = None
    carryover_likely: bool = False
    pace_label: str | None = None


class DashboardStatusCount(BaseModel):
    status: str
    count: int


class DashboardAgingItem(BaseModel):
    id: uuid.UUID
    title: str
    days: float
    status: str
    entity_type: str


class DashboardDueItem(BaseModel):
    id: uuid.UUID
    title: str
    due_date: datetime
    status: str


class DashboardFlow(BaseModel):
    by_status: list[DashboardStatusCount] = Field(default_factory=list)
    aging_wip: list[DashboardAgingItem] = Field(default_factory=list)
    due_soon: list[DashboardDueItem] = Field(default_factory=list)


class DashboardAssigneeLoad(BaseModel):
    assignee_id: uuid.UUID | None = None
    name: str
    open_points: float = 0
    open_tasks: int = 0
    capacity_points: int | None = None


class DashboardLoad(BaseModel):
    by_assignee: list[DashboardAssigneeLoad] = Field(default_factory=list)


class DashboardEpicHealth(BaseModel):
    id: uuid.UUID
    title: str
    done_stories: int
    total_stories: int
    percent_done: float | None = None


class ProjectDashboardResponse(BaseModel):
    project_id: uuid.UUID
    active_sprint: DashboardSprint | None = None
    progress: DashboardProgress
    time: DashboardTime
    velocity: DashboardVelocity
    risks: DashboardRisks
    flow: DashboardFlow
    load: DashboardLoad
    epic_health: list[DashboardEpicHealth] = Field(default_factory=list)
    message: str | None = None
