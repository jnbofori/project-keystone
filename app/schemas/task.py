import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationSource, TaskPriority, TaskStatus
from app.schemas.team_member import TeamMemberSummary


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    external_key: str | None = None
    source: IntegrationSource = IntegrationSource.manual
    status: TaskStatus = TaskStatus.backlog
    priority: TaskPriority = TaskPriority.medium
    story_points: int | None = None
    assignee_id: uuid.UUID | None = None
    sprint_id: uuid.UUID | None = None
    epic_id: uuid.UUID | None = None
    story_id: uuid.UUID | None = None
    started_at: datetime | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    depends_on_task_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskDependencyResponse(BaseModel):
    id: uuid.UUID
    depends_on_task_id: uuid.UUID
    depends_on_external_key: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    external_key: str | None
    source: IntegrationSource
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    story_points: int | None
    assignee_id: uuid.UUID | None
    assignee: TeamMemberSummary | None = None
    sprint_id: uuid.UUID | None
    epic_id: uuid.UUID | None
    story_id: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    due_date: datetime | None
    completed_at: datetime | None
    updated_at: datetime
    dependencies: list[TaskDependencyResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
