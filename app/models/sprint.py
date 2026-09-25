from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IntegrationSource, SprintStatus

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.sprint_requirement_baseline import SprintRequirementBaseline
    from app.models.story import Story
    from app.models.task import Task


class Sprint(Base):
    __tablename__ = "sprints"
    __table_args__ = (
        Index(
            "uq_sprint_project_source_external_key",
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SprintStatus] = mapped_column(
        Enum(SprintStatus, name="sprint_status"),
        default=SprintStatus.planned,
        nullable=False,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="sprints")
    stories: Mapped[list["Story"]] = relationship(back_populates="sprint")
    tasks: Mapped[list["Task"]] = relationship(back_populates="sprint")
    requirement_baselines: Mapped[list["SprintRequirementBaseline"]] = relationship(
        back_populates="sprint",
        cascade="all, delete-orphan",
    )
