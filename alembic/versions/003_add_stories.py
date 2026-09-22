"""add stories

Revision ID: 003
Revises: 002
Create Date: 2026-09-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'story'")
    op.execute("ALTER TYPE project_event_type ADD VALUE IF NOT EXISTS 'StoryCreated'")

    story_status = postgresql.ENUM(
        "todo", "in_progress", "done", "cancelled", name="story_status", create_type=False
    )
    story_status.create(op.get_bind(), checkfirst=True)

    integration_source = postgresql.ENUM(
        "jira",
        "github",
        "slack",
        "ci",
        "manual",
        "system",
        name="integration_source",
        create_type=False,
    )
    task_priority = postgresql.ENUM(
        "lowest", "low", "medium", "high", "highest", name="task_priority", create_type=False
    )

    op.create_table(
        "stories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", story_status, nullable=False),
        sa.Column("priority", task_priority, nullable=False),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column("epic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sprint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["team_members.id"]),
        sa.ForeignKeyConstraint(["epic_id"], ["epics.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_story_project_source_external_key",
        "stories",
        ["project_id", "source", "external_key"],
        unique=True,
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )

    op.add_column("tasks", sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_tasks_story_id_stories", "tasks", "stories", ["story_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_tasks_story_id_stories", "tasks", type_="foreignkey")
    op.drop_column("tasks", "story_id")
    op.drop_index("uq_story_project_source_external_key", table_name="stories")
    op.drop_table("stories")
    op.execute("DROP TYPE IF EXISTS story_status")
