from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_migrations_upgrade_and_downgrade_phase_two_a(tmp_path: Path) -> None:
    database = tmp_path / "migrated.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")

    command.upgrade(config, "head")

    inspector = inspect(create_engine(f"sqlite:///{database}"))
    tables = set(inspector.get_table_names())
    assert {"runs", "calls", "call_attempts", "run_transitions"} <= tables
    assert {
        "attempt_id",
        "call_id",
        "ordinal",
        "kind",
        "status",
        "next_retry_at",
    } <= {column["name"] for column in inspector.get_columns("call_attempts")}
    assert {
        "uncached_input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "model_alias",
    } <= {column["name"] for column in inspector.get_columns("calls")}
    assert "reserved_cost_rmb" in {
        column["name"] for column in inspector.get_columns("runs")
    }

    command.downgrade(config, "base")

    assert set(inspect(create_engine(f"sqlite:///{database}")).get_table_names()) == {
        "alembic_version"
    }


def test_phase_two_a_migration_preserves_phase_one_calls(tmp_path: Path) -> None:
    database = tmp_path / "phase-one.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.upgrade(config, "20260818_0001")
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO runs (run_id, state, request_json) "
                "VALUES ('R-OLD-001', 'COMPLETED', '{}')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO calls "
                "(run_id, role, context_hash, prompt_hash, status) VALUES "
                "('R-OLD-001', 'fixture_qwen', :hash, :hash, 'SUCCEEDED')"
            ),
            {"hash": "a" * 64},
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                "SELECT role, model_alias, status FROM calls WHERE run_id = 'R-OLD-001'"
            )
        ).one()
    assert migrated == ("fixture_qwen", "fixture_qwen", "SUCCEEDED")
