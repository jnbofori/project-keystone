import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationSource, StoryStatus, TaskPriority
from app.schemas.team_member import TeamMemberSummary


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    external_key: str | None = None
    source: IntegrationSource = IntegrationSource.manual
    status: StoryStatus = StoryStatus.todo
    priority: TaskPriority = TaskPriority.medium
    story_points: int | None = None
    epic_id: uuid.UUID | None = None
    sprint_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None


class StoryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    external_key: str | None
    source: IntegrationSource
    title: str
    description: str | None
    status: StoryStatus
    priority: TaskPriority
    story_points: int | None
    epic_id: uuid.UUID | None
    sprint_id: uuid.UUID | None
    assignee_id: uuid.UUID | None
    assignee: TeamMemberSummary | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
