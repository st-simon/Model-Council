"""Create the Phase 1 offline blind-review schema.

Revision ID: 20260818_0001
Revises:
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_table(
        "calls",
        sa.Column("call_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("actual_model_id", sa.String(length=200), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_rmb", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"]),
        sa.PrimaryKeyConstraint("call_id"),
        sa.UniqueConstraint(
            "run_id", "role", "context_hash", "prompt_hash", name="uq_logical_call"
        ),
    )
    op.create_table(
        "run_transitions",
        sa.Column("transition_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("from_state", sa.String(length=50), nullable=False),
        sa.Column("to_state", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"]),
        sa.PrimaryKeyConstraint("transition_id"),
    )


def downgrade() -> None:
    op.drop_table("run_transitions")
    op.drop_table("calls")
    op.drop_table("runs")
