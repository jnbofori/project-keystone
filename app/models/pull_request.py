from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IntegrationSource, PullRequestStatus

if TYPE_CHECKING:
    from app.models.commit import Commit
    from app.models.project import Project
    from app.models.task import Task
    from app.models.team_member import TeamMember


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        Index(
            "uq_pr_project_source_external_key",
            "project_id",
            "source",
            "external_key",
            unique=True,
            postgresql_where=text("external_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    external_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[IntegrationSource] = mapped_column(
        Enum(IntegrationSource, name="integration_source", create_constraint=False),
        default=IntegrationSource.github,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PullRequestStatus] = mapped_column(
        Enum(PullRequestStatus, name="pull_request_status"),
        default=PullRequestStatus.open,
        nullable=False,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("team_members.id"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="pull_requests")
    author: Mapped["TeamMember | None"] = relationship(back_populates="authored_pull_requests")
    task: Mapped["Task | None"] = relationship(back_populates="pull_requests")
    commits: Mapped[list["Commit"]] = relationship(back_populates="pull_request")
