import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TeamMemberCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    user_id: uuid.UUID | None = None
    jira_account_id: str | None = None
    github_login: str | None = None
    slack_user_id: str | None = None
    role_title: str | None = None
    capacity_points: int | None = None
    is_active: bool = True


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    display_name: str
    email: str | None
    jira_account_id: str | None
    github_login: str | None
    slack_user_id: str | None
    role_title: str | None
    capacity_points: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    email: str | None = None

    model_config = {"from_attributes": True}
