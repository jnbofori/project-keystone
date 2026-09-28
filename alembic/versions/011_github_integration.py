"""github app installations, project repo links, PR/commit github fields

Revision ID: 011
Revises: 010
Create Date: 2026-09-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("account_login", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=True),
        sa.Column("account_avatar_url", sa.Text(), nullable=True),
        sa.Column("repository_selection", sa.String(length=32), nullable=True),
        sa.Column("connected_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("installation_id", name="uq_github_installations_installation_id"),
    )
    op.create_index("ix_github_installations_organization_id", "github_installations", ["organization_id"])

    op.create_table(
        "project_github_repos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "installation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("github_installations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repo_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("linked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("project_id", "repo_id", name="uq_project_github_repo"),
    )
    op.create_index("ix_project_github_repos_project_id", "project_github_repos", ["project_id"])
    op.create_index("ix_project_github_repos_repo_id", "project_github_repos", ["repo_id"])

    op.add_column(
        "pull_requests",
        sa.Column(
            "repo_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_github_repos.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column("pull_requests", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("pull_requests", sa.Column("github_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "pull_requests",
        sa.Column("draft", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("pull_requests", sa.Column("author_login", sa.String(length=255), nullable=True))
    op.add_column("pull_requests", sa.Column("head_branch", sa.String(length=255), nullable=True))
    op.add_column("pull_requests", sa.Column("base_branch", sa.String(length=255), nullable=True))
    op.add_column(
        "pull_requests",
        sa.Column(
            "jira_keys",
            postgresql.ARRAY(sa.String(length=64)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column("pull_requests", sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_pull_requests_repo_link_id", "pull_requests", ["repo_link_id"])

    op.add_column(
        "commits",
        sa.Column(
            "repo_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_github_repos.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column("commits", sa.Column("author_login", sa.String(length=255), nullable=True))
    op.add_column("commits", sa.Column("author_name", sa.String(length=255), nullable=True))
    op.add_column(
        "commits",
        sa.Column(
            "jira_keys",
            postgresql.ARRAY(sa.String(length=64)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.create_index("ix_commits_repo_link_id", "commits", ["repo_link_id"])


def downgrade() -> None:
    op.drop_index("ix_commits_repo_link_id", table_name="commits")
    for column in ("jira_keys", "author_name", "author_login", "repo_link_id"):
        op.drop_column("commits", column)

    op.drop_index("ix_pull_requests_repo_link_id", table_name="pull_requests")
    for column in (
        "github_updated_at",
        "jira_keys",
        "base_branch",
        "head_branch",
        "author_login",
        "draft",
        "github_id",
        "number",
        "repo_link_id",
    ):
        op.drop_column("pull_requests", column)

    op.drop_index("ix_project_github_repos_repo_id", table_name="project_github_repos")
    op.drop_index("ix_project_github_repos_project_id", table_name="project_github_repos")
    op.drop_table("project_github_repos")
    op.drop_index("ix_github_installations_organization_id", table_name="github_installations")
    op.drop_table("github_installations")
