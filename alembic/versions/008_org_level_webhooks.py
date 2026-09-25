"""org-level jira webhooks on jira_connections

Revision ID: 008
Revises: 007
Create Date: 2026-09-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jira_connections", sa.Column("webhook_id", sa.String(length=128), nullable=True))
    op.add_column("jira_connections", sa.Column("webhook_expiration", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jira_connections", sa.Column("webhook_secret", sa.String(length=128), nullable=True))

    # Prefer any existing project webhook metadata for the org connection
    op.execute(
        sa.text(
            """
            UPDATE jira_connections jc
            SET
                webhook_id = sub.webhook_id,
                webhook_expiration = sub.webhook_expiration,
                webhook_secret = sub.webhook_secret
            FROM (
                SELECT DISTINCT ON (p.organization_id)
                    p.organization_id,
                    p.webhook_id,
                    p.webhook_expiration,
                    p.webhook_secret
                FROM projects p
                WHERE p.webhook_id IS NOT NULL OR p.webhook_secret IS NOT NULL
                ORDER BY p.organization_id, p.webhook_expiration DESC NULLS LAST
            ) sub
            WHERE sub.organization_id = jc.organization_id
            """
        )
    )

    op.drop_column("projects", "webhook_secret")
    op.drop_column("projects", "webhook_expiration")
    op.drop_column("projects", "webhook_id")


def downgrade() -> None:
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
            WHERE jc.organization_id = p.organization_id
              AND p.jira_project_key IS NOT NULL
            """
        )
    )

    op.drop_column("jira_connections", "webhook_secret")
    op.drop_column("jira_connections", "webhook_expiration")
    op.drop_column("jira_connections", "webhook_id")
