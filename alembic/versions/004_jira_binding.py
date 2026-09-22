"""add jira project binding and event external_key

Revision ID: 004
Revises: 003
Create Date: 2026-09-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("jira_project_key", sa.String(length=64), nullable=True))
    op.add_column("projects", sa.Column("jira_project_id", sa.String(length=64), nullable=True))
    op.create_index(
        "uq_projects_jira_project_key",
        "projects",
        ["jira_project_key"],
        unique=True,
        postgresql_where=sa.text("jira_project_key IS NOT NULL"),
    )

    op.add_column("project_events", sa.Column("external_key", sa.String(length=255), nullable=True))
    op.create_index(
        "uq_project_events_project_source_external_key",
        "project_events",
        ["project_id", "source", "external_key"],
        unique=True,
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_project_events_project_source_external_key", table_name="project_events")
    op.drop_column("project_events", "external_key")
    op.drop_index("uq_projects_jira_project_key", table_name="projects")
    op.drop_column("projects", "jira_project_id")
    op.drop_column("projects", "jira_project_key")
