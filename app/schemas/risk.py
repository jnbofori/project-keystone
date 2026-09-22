import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationSource, RiskSeverity, RiskStatus


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    severity: RiskSeverity = RiskSeverity.medium
    status: RiskStatus = RiskStatus.open
    source: IntegrationSource = IntegrationSource.manual
    related_task_id: uuid.UUID | None = None
    detected_at: datetime | None = None
    resolved_at: datetime | None = None


class RiskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    severity: RiskSeverity
    status: RiskStatus
    source: IntegrationSource
    related_task_id: uuid.UUID | None
    detected_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
