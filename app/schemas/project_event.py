import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EntityType, IntegrationSource, ProjectEventType


class ProjectEventCreate(BaseModel):
    type: ProjectEventType
    source: IntegrationSource
    timestamp: datetime
    entity_type: EntityType | None = None
    entity_id: uuid.UUID | None = None
    external_entity_key: str | None = None
    actor_team_member_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class ProjectEventResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    type: ProjectEventType
    source: IntegrationSource
    entity_type: EntityType | None
    entity_id: uuid.UUID | None
    external_key: str | None = None
    external_entity_key: str | None
    actor_team_member_id: uuid.UUID | None
    timestamp: datetime
    metadata: dict[str, Any] | None = Field(validation_alias="metadata_", default=None)
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
