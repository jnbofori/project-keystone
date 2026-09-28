"""github branches table; task/story links on PRs, commits, branches

Revision ID: 012
Revises: 011
Create Date: 2026-09-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "repo_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_github_repos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("head_sha", sa.String(length=64), nullable=True),
        sa.Column(
            "jira_keys",
            postgresql.ARRAY(sa.String(length=64)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("repo_link_id", "name", name="uq_github_branch_repo_name"),
    )
    op.create_index("ix_github_branches_project_id", "github_branches", ["project_id"])

    op.drop_constraint("pull_requests_task_id_fkey", "pull_requests", type_="foreignkey")
    op.create_foreign_key(
        "pull_requests_task_id_fkey", "pull_requests", "tasks", ["task_id"], ["id"], ondelete="SET NULL"
    )
    op.add_column(
        "pull_requests",
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stories.id", ondelete="SET NULL", name="pull_requests_story_id_fkey"),
            nullable=True,
        ),
    )

    op.add_column(
        "commits",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="SET NULL", name="commits_task_id_fkey"),
            nullable=True,
        ),
    )
    op.add_column(
        "commits",
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stories.id", ondelete="SET NULL", name="commits_story_id_fkey"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("commits", "story_id")
    op.drop_column("commits", "task_id")

    op.drop_column("pull_requests", "story_id")
    op.drop_constraint("pull_requests_task_id_fkey", "pull_requests", type_="foreignkey")
    op.create_foreign_key("pull_requests_task_id_fkey", "pull_requests", "tasks", ["task_id"], ["id"])

    op.drop_index("ix_github_branches_project_id", table_name="github_branches")
    op.drop_table("github_branches")
