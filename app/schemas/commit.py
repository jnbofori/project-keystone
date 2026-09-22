import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.team_member import TeamMemberSummary


class CommitCreate(BaseModel):
    sha: str = Field(min_length=1, max_length=64)
    message: str | None = None
    url: str | None = None
    author_id: uuid.UUID | None = None
    committed_at: datetime | None = None
    pull_request_id: uuid.UUID | None = None


class CommitResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    sha: str
    message: str | None
    url: str | None
    author_id: uuid.UUID | None
    author: TeamMemberSummary | None = None
    committed_at: datetime | None
    pull_request_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
