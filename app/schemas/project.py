import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.project import ProjectRole


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    jira_project_key: str | None = None
    jira_project_id: str | None = None
    created_by: uuid.UUID
    created_at: datetime
    current_user_role: ProjectRole

    model_config = {"from_attributes": True}


class ProjectMemberCreate(BaseModel):
    email: str
    role: ProjectRole = ProjectRole.member


class ProjectMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    role: ProjectRole
    created_at: datetime
