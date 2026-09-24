"""organization tenancy and org-scoped jira

Revision ID: 007
Revises: 006
Create Date: 2026-09-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

organization_role = postgresql.ENUM("owner", "admin", "member", name="organization_role", create_type=False)


def upgrade() -> None:
    organization_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("invite_code", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )
    op.create_index("ix_organizations_invite_code", "organizations", ["invite_code"], unique=True)

    op.create_table(
        "organization_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("role", organization_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_organization_member"),
        sa.UniqueConstraint("user_id", name="uq_organization_member_user"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, invite_code, created_by, created_at)
            SELECT
                gen_random_uuid(),
                COALESCE(split_part(u.email, '@', 1), 'user') || '''s organization',
                replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', ''),
                u.id,
                now()
            FROM users u
            WHERE EXISTS (SELECT 1 FROM projects p WHERE p.created_by = u.id)
            """
        )
    )

    op.add_column("projects", sa.Column("organization_id", sa.UUID(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE projects p
            SET organization_id = o.id
            FROM organizations o
            WHERE o.created_by = p.created_by
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO organization_members (id, user_id, organization_id, role, created_at)
            SELECT gen_random_uuid(), o.created_by, o.id, 'owner', now()
            FROM organizations o
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO organization_members (id, user_id, organization_id, role, created_at)
            SELECT DISTINCT ON (pm.user_id)
                gen_random_uuid(),
                pm.user_id,
                p.organization_id,
                'member',
                now()
            FROM project_members pm
            JOIN projects p ON p.id = pm.project_id
            WHERE p.organization_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM organization_members om WHERE om.user_id = pm.user_id
              )
            ORDER BY pm.user_id, pm.created_at ASC
            """
        )
    )

    op.execute(
        sa.text(
            """
            WITH new_orgs AS (
                INSERT INTO organizations (id, name, invite_code, created_by, created_at)
                SELECT
                    gen_random_uuid(),
                    COALESCE(split_part(u.email, '@', 1), 'user') || '''s organization',
                    replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', ''),
                    u.id,
                    now()
                FROM users u
                WHERE NOT EXISTS (
                    SELECT 1 FROM organization_members om WHERE om.user_id = u.id
                )
                RETURNING id, created_by
            )
            INSERT INTO organization_members (id, user_id, organization_id, role, created_at)
            SELECT gen_random_uuid(), created_by, id, 'owner', now()
            FROM new_orgs
            """
        )
    )

    op.alter_column("projects", "organization_id", nullable=False)
    op.create_foreign_key(
        "fk_projects_organization_id",
        "projects",
        "organizations",
        ["organization_id"],
        ["id"],
    )

    op.add_column("projects", sa.Column("webhook_id", sa.String(length=128), nullable=True))
    op.add_column("projects", sa.Column("webhook_expiration", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("webhook_secret", sa.String(length=128), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE projects p
            SET
                webhook_id = jc.webhook_id,
                webhook_expiration = jc.webhook_expiration,
                webhook_secret = jc.webhook_secret
            FROM jira_connections jc
            WHERE jc.project_id = p.id
            """
        )
    )

    op.add_column("jira_connections", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE jira_connections jc
            SET organization_id = p.organization_id
            FROM projects p
            WHERE p.id = jc.project_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM jira_connections
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY organization_id
                               ORDER BY updated_at DESC NULLS LAST, created_at DESC
                           ) AS rn
                    FROM jira_connections
                    WHERE organization_id IS NOT NULL
                ) ranked
                WHERE rn > 1
            )
            """
        )
    )

    op.alter_column("jira_connections", "organization_id", nullable=False)
    op.create_foreign_key(
        "fk_jira_connections_organization_id",
        "jira_connections",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_jira_connection_organization",
        "jira_connections",
        ["organization_id"],
    )

    op.drop_constraint("uq_jira_connection_project", "jira_connections", type_="unique")
    op.drop_constraint("jira_connections_project_id_fkey", "jira_connections", type_="foreignkey")
    op.drop_column("jira_connections", "project_id")
    op.drop_column("jira_connections", "webhook_id")
    op.drop_column("jira_connections", "webhook_expiration")
    op.drop_column("jira_connections", "webhook_secret")

    op.drop_index("uq_projects_jira_project_key", table_name="projects")
    op.create_index(
        "uq_projects_org_jira_project_key",
        "projects",
        ["organization_id", "jira_project_key"],
        unique=True,
        postgresql_where=sa.text("jira_project_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_projects_org_jira_project_key", table_name="projects")
    op.create_index(
        "uq_projects_jira_project_key",
        "projects",
        ["jira_project_key"],
        unique=True,
        postgresql_where=sa.text("jira_project_key IS NOT NULL"),
    )

    op.add_column("jira_connections", sa.Column("webhook_secret", sa.String(length=128), nullable=True))
    op.add_column("jira_connections", sa.Column("webhook_expiration", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jira_connections", sa.Column("webhook_id", sa.String(length=128), nullable=True))
    op.add_column("jira_connections", sa.Column("project_id", sa.UUID(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE jira_connections jc
            SET
                project_id = sub.project_id,
                webhook_id = sub.webhook_id,
                webhook_expiration = sub.webhook_expiration,
                webhook_secret = sub.webhook_secret
            FROM (
                SELECT DISTINCT ON (p.organization_id)
                    p.organization_id,
                    p.id AS project_id,
                    p.webhook_id,
                    p.webhook_expiration,
                    p.webhook_secret
                FROM projects p
                ORDER BY p.organization_id, p.created_at ASC
            ) sub
            WHERE sub.organization_id = jc.organization_id
            """
        )
    )

    op.alter_column("jira_connections", "project_id", nullable=False)
    op.create_foreign_key(
        "jira_connections_project_id_fkey",
        "jira_connections",
        "projects",
        ["project_id"],
        ["id"],
    )
    op.create_unique_constraint("uq_jira_connection_project", "jira_connections", ["project_id"])
    op.drop_constraint("uq_jira_connection_organization", "jira_connections", type_="unique")
    op.drop_constraint("fk_jira_connections_organization_id", "jira_connections", type_="foreignkey")
    op.drop_column("jira_connections", "organization_id")

    op.drop_column("projects", "webhook_secret")
    op.drop_column("projects", "webhook_expiration")
    op.drop_column("projects", "webhook_id")
    op.drop_constraint("fk_projects_organization_id", "projects", type_="foreignkey")
    op.drop_column("projects", "organization_id")

    op.drop_table("organization_members")
    op.drop_index("ix_organizations_invite_code", table_name="organizations")
    op.drop_table("organizations")
    organization_role.drop(op.get_bind(), checkfirst=True)
