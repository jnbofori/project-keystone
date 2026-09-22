import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationSource, PullRequestStatus
from app.schemas.team_member import TeamMemberSummary


class PullRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    external_key: str | None = None
    source: IntegrationSource = IntegrationSource.github
    url: str | None = None
    status: PullRequestStatus = PullRequestStatus.open
    author_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    opened_at: datetime | None = None
    merged_at: datetime | None = None
    closed_at: datetime | None = None


class PullRequestResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    external_key: str | None
    source: IntegrationSource
    title: str
    url: str | None
    status: PullRequestStatus
    author_id: uuid.UUID | None
    author: TeamMemberSummary | None = None
    task_id: uuid.UUID | None
    opened_at: datetime | None
    merged_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
