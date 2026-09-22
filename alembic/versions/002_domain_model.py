"""domain model for delivery entities

Revision ID: 002
Revises: 001
Create Date: 2026-09-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    integration_source.create(op.get_bind(), checkfirst=True)

    sprint_status = postgresql.ENUM(
        "planned", "active", "completed", name="sprint_status", create_type=False
    )
    sprint_status.create(op.get_bind(), checkfirst=True)

    epic_status = postgresql.ENUM(
        "todo", "in_progress", "done", "cancelled", name="epic_status", create_type=False
    )
    epic_status.create(op.get_bind(), checkfirst=True)

    task_status = postgresql.ENUM(
        "backlog",
        "todo",
        "in_progress",
        "blocked",
        "in_review",
        "done",
        "cancelled",
        name="task_status",
        create_type=False,
    )
    task_status.create(op.get_bind(), checkfirst=True)

    task_priority = postgresql.ENUM(
        "lowest", "low", "medium", "high", "highest", name="task_priority", create_type=False
    )
    task_priority.create(op.get_bind(), checkfirst=True)

    pull_request_status = postgresql.ENUM(
        "open", "merged", "closed", name="pull_request_status", create_type=False
    )
    pull_request_status.create(op.get_bind(), checkfirst=True)

    risk_severity = postgresql.ENUM(
        "low", "medium", "high", "critical", name="risk_severity", create_type=False
    )
    risk_severity.create(op.get_bind(), checkfirst=True)

    risk_status = postgresql.ENUM(
        "open", "mitigating", "resolved", "accepted", name="risk_status", create_type=False
    )
    risk_status.create(op.get_bind(), checkfirst=True)

    entity_type = postgresql.ENUM(
        "task",
        "sprint",
        "epic",
        "pull_request",
        "commit",
        "discussion",
        "risk",
        "team_member",
        "project",
        name="entity_type",
        create_type=False,
    )
    entity_type.create(op.get_bind(), checkfirst=True)

    project_event_type = postgresql.ENUM(
        "TaskCreated",
        "TaskMoved",
        "TaskCompleted",
        "TaskReopened",
        "StoryPointsChanged",
        "DeadlineChanged",
        "AssigneeChanged",
        "DependencyAdded",
        "SprintStarted",
        "SprintCompleted",
        "EpicCreated",
        "PullRequestOpened",
        "PullRequestMerged",
        "PullRequestClosed",
        "BuildFailed",
        "BuildSucceeded",
        "CommitPushed",
        "RequirementAdded",
        "ScopeChanged",
        "SlackRiskMentioned",
        "RiskOpened",
        "RiskResolved",
        "DiscussionPosted",
        name="project_event_type",
        create_type=False,
    )
    project_event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("jira_account_id", sa.String(length=255), nullable=True),
        sa.Column("github_login", sa.String(length=255), nullable=True),
        sa.Column("slack_user_id", sa.String(length=255), nullable=True),
        sa.Column("role_title", sa.String(length=255), nullable=True),
        sa.Column("capacity_points", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_team_member_project_user",
        "team_members",
        ["project_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_team_member_project_jira",
        "team_members",
        ["project_id", "jira_account_id"],
        unique=True,
        postgresql_where=sa.text("jira_account_id IS NOT NULL"),
    )
    op.create_index(
        "uq_team_member_project_github",
        "team_members",
        ["project_id", "github_login"],
        unique=True,
        postgresql_where=sa.text("github_login IS NOT NULL"),
    )
    op.create_index(
        "uq_team_member_project_slack",
        "team_members",
        ["project_id", "slack_user_id"],
        unique=True,
        postgresql_where=sa.text("slack_user_id IS NOT NULL"),
    )

    op.create_table(
        "sprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("status", sprint_status, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_sprint_project_source_external_key",
        "sprints",
        ["project_id", "source", "external_key"],
        unique=True,
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )

    op.create_table(
        "epics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", epic_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_epic_project_source_external_key",
        "epics",
        ["project_id", "source", "external_key"],
        unique=True,
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, nullable=False),
        sa.Column("priority", task_priority, nullable=False),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sprint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("epic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["team_members.id"]),
        sa.ForeignKeyConstraint(["epic_id"], ["epics.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_task_project_source_external_key",
        "tasks",
        ["project_id", "source", "external_key"],
        unique=True,
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )

    op.create_table(
        "task_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depends_on_task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("task_id != depends_on_task_id", name="ck_task_dependency_no_self"),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
    )

    op.create_table(
        "pull_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("status", pull_request_status, nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["team_members.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_pr_project_source_external_key",
        "pull_requests",
        ["project_id", "source", "external_key"],
        unique=True,
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )

    op.create_table(
        "commits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sha", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pull_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["team_members.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "sha", name="uq_commit_project_sha"),
    )

    op.create_table(
        "discussions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("channel_or_location", sa.String(length=512), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["team_members.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "risks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", risk_severity, nullable=False),
        sa.Column("status", risk_status, nullable=False),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("related_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["related_task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "project_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", project_event_type, nullable=False),
        sa.Column("source", integration_source, nullable=False),
        sa.Column("entity_type", entity_type, nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_entity_key", sa.String(length=255), nullable=True),
        sa.Column("actor_team_member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_team_member_id"], ["team_members.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_events_project_timestamp", "project_events", ["project_id", "timestamp"])
    op.create_index("ix_project_events_project_type", "project_events", ["project_id", "type"])
    op.create_index("ix_project_events_entity", "project_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_project_events_entity", table_name="project_events")
    op.drop_index("ix_project_events_project_type", table_name="project_events")
    op.drop_index("ix_project_events_project_timestamp", table_name="project_events")
    op.drop_table("project_events")
    op.drop_table("risks")
    op.drop_table("discussions")
    op.drop_table("commits")
    op.drop_index("uq_pr_project_source_external_key", table_name="pull_requests")
    op.drop_table("pull_requests")
    op.drop_table("task_dependencies")
    op.drop_index("uq_task_project_source_external_key", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("uq_epic_project_source_external_key", table_name="epics")
    op.drop_table("epics")
    op.drop_index("uq_sprint_project_source_external_key", table_name="sprints")
    op.drop_table("sprints")
    op.drop_index("uq_team_member_project_slack", table_name="team_members")
    op.drop_index("uq_team_member_project_github", table_name="team_members")
    op.drop_index("uq_team_member_project_jira", table_name="team_members")
    op.drop_index("uq_team_member_project_user", table_name="team_members")
    op.drop_table("team_members")

    op.execute("DROP TYPE IF EXISTS project_event_type")
    op.execute("DROP TYPE IF EXISTS entity_type")
    op.execute("DROP TYPE IF EXISTS risk_status")
    op.execute("DROP TYPE IF EXISTS risk_severity")
    op.execute("DROP TYPE IF EXISTS pull_request_status")
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS epic_status")
    op.execute("DROP TYPE IF EXISTS sprint_status")
    op.execute("DROP TYPE IF EXISTS integration_source")
