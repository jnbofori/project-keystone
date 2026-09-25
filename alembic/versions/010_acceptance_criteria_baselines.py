"""acceptance criteria + sprint requirement baselines

Revision ID: 010
Revises: 009
Create Date: 2026-09-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

entity_type_enum = postgresql.ENUM(
    "task",
    "sprint",
    "epic",
    "story",
    "pull_request",
    "commit",
    "discussion",
    "risk",
    "team_member",
    "project",
    name="entity_type",
    create_type=False,
)


def upgrade() -> None:
    op.add_column("stories", sa.Column("acceptance_criteria", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("acceptance_criteria", sa.Text(), nullable=True))

    op.create_table(
        "sprint_requirement_baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "sprint_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sprints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", entity_type_enum, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria", sa.Text(), nullable=True),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "sprint_id",
            "entity_type",
            "entity_id",
            name="uq_sprint_requirement_baseline",
        ),
    )
    op.create_index(
        "ix_sprint_requirement_baselines_sprint",
        "sprint_requirement_baselines",
        ["sprint_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_sprint_requirement_baselines_sprint", table_name="sprint_requirement_baselines")
    op.drop_table("sprint_requirement_baselines")
    op.drop_column("tasks", "acceptance_criteria")
    op.drop_column("stories", "acceptance_criteria")
