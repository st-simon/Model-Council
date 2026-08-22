from __future__ import annotations

from pathlib import Path

import pytest

from model_council.adapters.sqlite import SQLiteRunStore
from model_council.models import (
    AttemptKind,
    AttemptStatus,
    BudgetPolicy,
    CallStatus,
    ReviewInput,
    RunState,
)

RUN_ID = "R-GATE-C-QWEN-BEIJING-001"
ERROR_CODE = "LOCAL_PROXY_PREFLIGHT_FAILED"


def _running_preprovider_store(tmp_path: Path) -> SQLiteRunStore:
    store = SQLiteRunStore(tmp_path / "council.db")
    request = ReviewInput(
        project_id="gate-c-qwen-beijing-public",
        run_id=RUN_ID,
        proposal="public fixture",
        reviewers=["capability_probe"],
        budget=BudgetPolicy(hard_limit_rmb=0.2),
    )
    store.create_or_load(request)
    store.transition(RUN_ID, RunState.BLIND_REVIEW_RUNNING)
    store.claim_call(RUN_ID, "capability_probe", "architect_primary_v1", "c", "p")
    store.start_attempt(RUN_ID, "capability_probe", AttemptKind.REVIEW)
    return store


def test_reconcile_preprovider_failure_closes_exactly_one_untouched_attempt(
    tmp_path: Path,
) -> None:
    store = _running_preprovider_store(tmp_path)

    changed = store.reconcile_preprovider_failure(RUN_ID, ERROR_CODE)

    assert changed is True
    assert store.load_state(RUN_ID) == RunState.FAILED
    call = store.list_calls(RUN_ID)[0]
    attempt = store.list_attempts(RUN_ID)[0]
    assert call.status == CallStatus.FAILED_TERMINAL
    assert call.error_code == ERROR_CODE
    assert call.provider_request_id is None
    assert attempt.status == AttemptStatus.FAILED_TERMINAL
    assert attempt.error_code == ERROR_CODE
    assert attempt.provider_request_id is None
    assert store.reconcile_preprovider_failure(RUN_ID, ERROR_CODE) is False


def test_reconcile_preprovider_failure_rejects_any_provider_evidence(
    tmp_path: Path,
) -> None:
    store = _running_preprovider_store(tmp_path)
    attempt = store.list_attempts(RUN_ID)[0]
    with store.engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE call_attempts SET provider_request_id = ? WHERE attempt_id = ?",
            ("req-provider-observed", attempt.attempt_id),
        )

    with pytest.raises(ValueError, match="not an untouched pre-provider attempt"):
        store.reconcile_preprovider_failure(RUN_ID, ERROR_CODE)

    assert store.load_state(RUN_ID) == RunState.BLIND_REVIEW_RUNNING
