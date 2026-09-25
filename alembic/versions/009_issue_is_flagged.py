"""add is_flagged to stories and tasks

Revision ID: 009
Revises: 008
Create Date: 2026-09-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "tasks",
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("tasks", "is_flagged")
    op.drop_column("stories", "is_flagged")
