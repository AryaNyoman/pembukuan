"""Add transaction source column.

Revision ID: 0002_source
Revises: 0001_initial
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_source"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("source", sa.String(32), nullable=False, server_default="telegram"),
    )


def downgrade() -> None:
    op.drop_column("transactions", "source")
