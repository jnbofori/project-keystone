import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import EpicStatus, IntegrationSource


class EpicCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    external_key: str | None = None
    source: IntegrationSource = IntegrationSource.manual
    status: EpicStatus = EpicStatus.todo


class EpicResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    external_key: str | None
    source: IntegrationSource
    title: str
    description: str | None
    status: EpicStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
