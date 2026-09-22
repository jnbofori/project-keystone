from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.commit import Commit
    from app.models.discussion import Discussion
    from app.models.document import Document
    from app.models.epic import Epic
    from app.models.jira_connection import JiraConnection
    from app.models.project_event import ProjectEvent
    from app.models.pull_request import PullRequest
    from app.models.query_log import QueryLog
    from app.models.risk import Risk
    from app.models.sprint import Sprint
    from app.models.story import Story
    from app.models.task import Task
    from app.models.team_member import TeamMember
    from app.models.user import User


class ProjectRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


ROLE_RANK = {
    ProjectRole.viewer: 0,
    ProjectRole.member: 1,
    ProjectRole.admin: 2,
    ProjectRole.owner: 3,
}


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index(
            "uq_projects_jira_project_key",
            "jira_project_key",
            unique=True,
            postgresql_where=text("jira_project_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    jira_project_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    jira_project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    query_logs: Mapped[list["QueryLog"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    team_members: Mapped[list["TeamMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sprints: Mapped[list["Sprint"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    epics: Mapped[list["Epic"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    stories: Mapped[list["Story"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    commits: Mapped[list["Commit"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    discussions: Mapped[list["Discussion"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    risks: Mapped[list["Risk"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    events: Mapped[list["ProjectEvent"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jira_connection: Mapped["JiraConnection | None"] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("user_id", "project_id", name="uq_project_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole, name="project_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="memberships")
    project: Mapped["Project"] = relationship(back_populates="members")
