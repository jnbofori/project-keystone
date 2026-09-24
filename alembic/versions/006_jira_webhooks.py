"""add jira webhook fields on jira_connections

Revision ID: 006
Revises: 005
Create Date: 2026-09-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jira_connections", sa.Column("webhook_id", sa.String(length=128), nullable=True))
    op.add_column("jira_connections", sa.Column("webhook_expiration", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jira_connections", sa.Column("webhook_secret", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("jira_connections", "webhook_secret")
    op.drop_column("jira_connections", "webhook_expiration")
    op.drop_column("jira_connections", "webhook_id")
