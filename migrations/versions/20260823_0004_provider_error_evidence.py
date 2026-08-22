"""Persist sanitized provider error evidence.

Revision ID: 20260823_0004
Revises: 20260821_0003
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0004"
down_revision: str | None = "20260821_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("calls", "call_attempts"):
        op.add_column(
            table,
            sa.Column("provider_error_code", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    for table in ("call_attempts", "calls"):
        op.drop_column(table, "provider_error_code")
