"""Persist provider request and pricing evidence.

Revision ID: 20260821_0003
Revises: 20260821_0002
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_0003"
down_revision: str | None = "20260821_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("calls", "call_attempts"):
        op.add_column(
            table,
            sa.Column("provider_request_id", sa.String(length=200), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("pricing_snapshot_id", sa.String(length=200), nullable=True),
        )


def downgrade() -> None:
    for table in ("call_attempts", "calls"):
        op.drop_column(table, "pricing_snapshot_id")
        op.drop_column(table, "provider_request_id")
