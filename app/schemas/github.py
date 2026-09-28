import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PullRequestStatus


class GithubInstallStartResponse(BaseModel):
    install_url: str


class GithubInstallation(BaseModel):
    id: uuid.UUID
    installation_id: int
    account_login: str
    account_type: str | None = None
    account_avatar_url: str | None = None
    repository_selection: str | None = None
    connected_by: uuid.UUID
    suspended_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GithubRepoSummary(BaseModel):
    repo_id: int
    full_name: str
    private: bool = False
    default_branch: str | None = None
    html_url: str | None = None
    installation_id: uuid.UUID
    account_login: str


class GithubRepoLinkRequest(BaseModel):
    repo_ids: list[int] = Field(default_factory=list, max_length=50)


class GithubLinkedRepo(BaseModel):
    id: uuid.UUID
    repo_id: int
    full_name: str
    default_branch: str | None = None
    html_url: str | None = None
    installation_id: uuid.UUID
    last_synced_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GithubSyncErrorItem(BaseModel):
    repo: str
    message: str


class GithubSyncResponse(BaseModel):
    project_id: uuid.UUID
    repos: int = 0
    pull_requests: int = 0
    commits: int = 0
    errors: list[GithubSyncErrorItem] = Field(default_factory=list)


class GithubPullRequestItem(BaseModel):
    id: uuid.UUID
    repo_full_name: str | None = None
    number: int | None = None
    title: str
    url: str | None = None
    status: PullRequestStatus
    draft: bool = False
    author_login: str | None = None
    head_branch: str | None = None
    base_branch: str | None = None
    jira_keys: list[str] = Field(default_factory=list)
    opened_at: datetime | None = None
    merged_at: datetime | None = None
    closed_at: datetime | None = None
    github_updated_at: datetime | None = None


class GithubCommitItem(BaseModel):
    id: uuid.UUID
    repo_full_name: str | None = None
    sha: str
    message: str | None = None
    url: str | None = None
    author_login: str | None = None
    author_name: str | None = None
    committed_at: datetime | None = None
    jira_keys: list[str] = Field(default_factory=list)


class GithubActivityResponse(BaseModel):
    pull_requests: list[GithubPullRequestItem] = Field(default_factory=list)
    commits: list[GithubCommitItem] = Field(default_factory=list)
