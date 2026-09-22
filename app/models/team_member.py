from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.commit import Commit
    from app.models.discussion import Discussion
    from app.models.project import Project
    from app.models.project_event import ProjectEvent
    from app.models.pull_request import PullRequest
    from app.models.story import Story
    from app.models.task import Task
    from app.models.user import User


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        Index(
            "uq_team_member_project_user",
            "project_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_team_member_project_jira",
            "project_id",
            "jira_account_id",
            unique=True,
            postgresql_where=text("jira_account_id IS NOT NULL"),
        ),
        Index(
            "uq_team_member_project_github",
            "project_id",
            "github_login",
            unique=True,
            postgresql_where=text("github_login IS NOT NULL"),
        ),
        Index(
            "uq_team_member_project_slack",
            "project_id",
            "slack_user_id",
            unique=True,
            postgresql_where=text("slack_user_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capacity_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="team_members")
    user: Mapped["User | None"] = relationship(back_populates="team_memberships")
    assigned_tasks: Mapped[list["Task"]] = relationship(back_populates="assignee")
    assigned_stories: Mapped[list["Story"]] = relationship(back_populates="assignee")
    authored_pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="author")
    authored_commits: Mapped[list["Commit"]] = relationship(back_populates="author")
    authored_discussions: Mapped[list["Discussion"]] = relationship(back_populates="author")
    acted_events: Mapped[list["ProjectEvent"]] = relationship(back_populates="actor")
