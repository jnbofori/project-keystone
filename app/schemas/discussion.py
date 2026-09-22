import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import IntegrationSource
from app.schemas.team_member import TeamMemberSummary


class DiscussionCreate(BaseModel):
    source: IntegrationSource
    body: str = Field(min_length=1)
    external_key: str | None = None
    channel_or_location: str | None = None
    author_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    occurred_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class DiscussionResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source: IntegrationSource
    external_key: str | None
    channel_or_location: str | None
    author_id: uuid.UUID | None
    author: TeamMemberSummary | None = None
    body: str
    task_id: uuid.UUID | None
    occurred_at: datetime | None
    created_at: datetime
    metadata: dict[str, Any] | None = Field(validation_alias="metadata_", default=None)

    model_config = {"from_attributes": True, "populate_by_name": True}
