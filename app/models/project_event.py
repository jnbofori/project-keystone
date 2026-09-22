from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EntityType, IntegrationSource, ProjectEventType

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.team_member import TeamMember


class ProjectEvent(Base):
    __tablename__ = "project_events"
    __table_args__ = (
        Index("ix_project_events_project_timestamp", "project_id", "timestamp"),
        Index("ix_project_events_project_type", "project_id", "type"),
        Index("ix_project_events_entity", "entity_type", "entity_id"),
        Index(
            "uq_project_events_project_source_external_key",
            "project_id",
            "source",
            "external_key",
            unique=True,
            postgresql_where=text("external_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    type: Mapped[ProjectEventType] = mapped_column(
        Enum(ProjectEventType, name="project_event_type"),
        nullable=False,
    )
    source: Mapped[IntegrationSource] = mapped_column(
        Enum(IntegrationSource, name="integration_source", create_constraint=False),
        nullable=False,
    )
    entity_type: Mapped[EntityType | None] = mapped_column(
        Enum(EntityType, name="entity_type"),
        nullable=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    external_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_entity_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_team_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("team_members.id"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="events")
    actor: Mapped["TeamMember | None"] = relationship(back_populates="acted_events")
