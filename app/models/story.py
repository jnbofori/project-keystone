from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IntegrationSource, StoryStatus, TaskPriority

if TYPE_CHECKING:
    from app.models.epic import Epic
    from app.models.project import Project
    from app.models.sprint import Sprint
    from app.models.task import Task
    from app.models.team_member import TeamMember


class Story(Base):
    __tablename__ = "stories"
    __table_args__ = (
        Index(
            "uq_story_project_source_external_key",
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
        default=IntegrationSource.manual,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus, name="story_status"),
        default=StoryStatus.todo,
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", create_constraint=False),
        default=TaskPriority.medium,
        nullable=False,
    )
    story_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    epic_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("epics.id"), nullable=True)
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sprints.id"), nullable=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("team_members.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="stories")
    epic: Mapped["Epic | None"] = relationship(back_populates="stories")
    sprint: Mapped["Sprint | None"] = relationship(back_populates="stories")
    assignee: Mapped["TeamMember | None"] = relationship(back_populates="assigned_stories")
    tasks: Mapped[list["Task"]] = relationship(back_populates="story")
