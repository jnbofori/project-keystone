import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationSource, SprintStatus


class SprintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    goal: str | None = None
    external_key: str | None = None
    source: IntegrationSource = IntegrationSource.manual
    status: SprintStatus = SprintStatus.planned
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    completed_at: datetime | None = None


class SprintResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    external_key: str | None
    source: IntegrationSource
    name: str
    goal: str | None
    status: SprintStatus
    starts_at: datetime | None
    ends_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
