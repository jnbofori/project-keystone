from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class JiraConnection(Base):
    __tablename__ = "jira_connections"
    __table_args__ = (UniqueConstraint("project_id", name="uq_jira_connection_project"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    cloud_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    site_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    connected_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    webhook_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    webhook_expiration: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="jira_connection")
    connector: Mapped["User"] = relationship()
