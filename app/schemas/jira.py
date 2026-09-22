import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JiraProjectSummary(BaseModel):
    id: str
    key: str
    name: str
    project_type_key: str | None = None


class JiraLinkRequest(BaseModel):
    jira_project_key: str | None = Field(
        default=None,
        description="Jira project key to link, or null to unlink",
        max_length=64,
    )


class JiraLinkResponse(BaseModel):
    project_id: uuid.UUID
    jira_project_key: str | None
    jira_project_id: str | None


class JiraSyncErrorItem(BaseModel):
    entity: str
    key: str | None = None
    message: str


class JiraSyncResponse(BaseModel):
    project_id: uuid.UUID
    jira_project_key: str
    team_members: int
    sprints: int
    epics: int
    stories: int
    tasks: int
    events: int
    errors: list[JiraSyncErrorItem] = Field(default_factory=list)


class JiraOAuthStartResponse(BaseModel):
    authorize_url: str


class JiraCloudSite(BaseModel):
    cloud_id: str
    site_url: str | None = None
    site_name: str | None = None


class JiraCloudSelectRequest(BaseModel):
    cloud_id: str = Field(min_length=1, max_length=128)


class JiraConnectionResponse(BaseModel):
    connected: bool
    cloud_id: str | None = None
    site_url: str | None = None
    site_name: str | None = None
    token_expires_at: datetime | None = None
    connected_by: uuid.UUID | None = None
    needs_site_selection: bool = False
    available_sites: list[JiraCloudSite] = Field(default_factory=list)
