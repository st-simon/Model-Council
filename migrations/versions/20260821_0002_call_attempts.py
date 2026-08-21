"""Add physical provider call attempts.

Revision ID: 20260821_0002
Revises: 20260818_0001
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_0002"
down_revision: str | None = "20260818_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "reserved_cost_rmb",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("calls", sa.Column("uncached_input_tokens", sa.Integer()))
    op.add_column("calls", sa.Column("cache_creation_input_tokens", sa.Integer()))
    op.add_column("calls", sa.Column("cache_read_input_tokens", sa.Integer()))
    op.add_column(
        "calls", sa.Column("model_alias", sa.String(length=100), nullable=True)
    )
    op.execute("UPDATE calls SET model_alias = role WHERE model_alias IS NULL")
    with op.batch_alter_table("calls", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_logical_call", type_="unique")
        batch_op.alter_column("model_alias", nullable=False)
        batch_op.create_unique_constraint(
            "uq_logical_call",
            ["run_id", "role", "model_alias", "context_hash", "prompt_hash"],
        )
    op.create_table(
        "call_attempts",
        sa.Column("attempt_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("call_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("actual_model_id", sa.String(length=200), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("uncached_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_creation_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_read_input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_rmb", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["call_id"], ["calls.call_id"]),
        sa.PrimaryKeyConstraint("attempt_id"),
        sa.UniqueConstraint("call_id", "ordinal", name="uq_call_attempt_ordinal"),
    )


def downgrade() -> None:
    op.drop_table("call_attempts")
    with op.batch_alter_table("calls", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_logical_call", type_="unique")
        batch_op.create_unique_constraint(
            "uq_logical_call",
            ["run_id", "role", "context_hash", "prompt_hash"],
        )
        batch_op.drop_column("model_alias")
    op.drop_column("calls", "cache_read_input_tokens")
    op.drop_column("calls", "cache_creation_input_tokens")
    op.drop_column("calls", "uncached_input_tokens")
    op.drop_column("runs", "reserved_cost_rmb")
