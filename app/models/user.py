from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.project import ProjectMember
    from app.models.query_log import QueryLog
    from app.models.team_member import TeamMember


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    memberships: Mapped[list["ProjectMember"]] = relationship(back_populates="user")
    documents: Mapped[list["Document"]] = relationship(back_populates="uploader")
    query_logs: Mapped[list["QueryLog"]] = relationship(back_populates="user")
    team_memberships: Mapped[list["TeamMember"]] = relationship(back_populates="user")
