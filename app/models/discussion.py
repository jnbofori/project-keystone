from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IntegrationSource

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task
    from app.models.team_member import TeamMember


class Discussion(Base):
    __tablename__ = "discussions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    source: Mapped[IntegrationSource] = mapped_column(
        Enum(IntegrationSource, name="integration_source", create_constraint=False),
        nullable=False,
    )
    external_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_or_location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("team_members.id"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="discussions")
    author: Mapped["TeamMember | None"] = relationship(back_populates="authored_discussions")
    task: Mapped["Task | None"] = relationship(back_populates="discussions")
