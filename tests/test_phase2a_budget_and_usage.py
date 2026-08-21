from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.budget import BudgetDisposition, BudgetGuard, HardBudgetExceeded
from model_council.models import BudgetPolicy, ReviewInput, RunState


def test_hard_budget_blocks_before_a_gateway_attempt(tmp_path: Path) -> None:
    gateway = FixtureModelGateway()
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=gateway,
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="budget-project",
        run_id="R-BUDGET-001",
        proposal="Review a transaction.",
        reviewers=["fixture_qwen"],
        budget=BudgetPolicy(
            soft_limit_rmb=0.005,
            hard_limit_rmb=0.01,
            estimated_call_cost_rmb=0.02,
            max_output_tokens=100,
        ),
    )

    summary = asyncio.run(application.start_review(request))

    assert summary.state == RunState.FAILED
    assert gateway.requests == []
    assert run_store.list_attempts(request.run_id) == []
    assert run_store.list_calls(request.run_id)[0].error_code == "BUDGET_HARD_LIMIT"


def test_concurrent_reviewers_cannot_overreserve_the_hard_budget(
    tmp_path: Path,
) -> None:
    gateway = FixtureModelGateway()
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=gateway,
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="budget-race-project",
        run_id="R-BUDGET-RACE-001",
        proposal="Review a transaction.",
        reviewers=["fixture_qwen", "fixture_kimi"],
        minimum_successful_reviewers=1,
        budget=BudgetPolicy(
            hard_limit_rmb=1.0,
            estimated_call_cost_rmb=0.6,
            max_output_tokens=100,
        ),
    )

    summary = asyncio.run(application.start_review(request))

    assert summary.state == RunState.COMPLETED
    assert len(gateway.requests) == 1
    assert len(run_store.list_attempts(request.run_id)) == 1
    assert {call.error_code for call in run_store.list_calls(request.run_id)} == {
        None,
        "BUDGET_HARD_LIMIT",
    }


def test_soft_budget_stops_only_optional_new_calls() -> None:
    policy = BudgetPolicy(
        soft_limit_rmb=1.0,
        hard_limit_rmb=2.0,
        estimated_call_cost_rmb=0.6,
        max_output_tokens=100,
    )
    guard = BudgetGuard()

    assert guard.check(policy, spent_rmb=0.6, required=True) == BudgetDisposition.ALLOW
    assert (
        guard.check(policy, spent_rmb=0.6, required=False)
        == BudgetDisposition.SOFT_STOP
    )
    with pytest.raises(HardBudgetExceeded):
        guard.check(policy, spent_rmb=1.5, required=True)


def test_cache_usage_is_preserved_in_state_attempts_and_logs(tmp_path: Path) -> None:
    gateway = FixtureModelGateway(behaviors={"fixture_qwen": "cached"})
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=gateway,
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="cache-project",
        run_id="R-CACHE-001",
        proposal="Review a transaction.",
        reviewers=["fixture_qwen"],
    )

    asyncio.run(application.start_review(request))

    call = run_store.list_calls(request.run_id)[0]
    attempt = run_store.list_attempts(request.run_id)[0]
    event = json.loads(
        (tmp_path / "logs" / "council.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    assert call.uncached_input_tokens == 0
    assert call.cache_read_input_tokens > 0
    assert call.cache_creation_input_tokens == 0
    assert attempt.cache_read_input_tokens == call.cache_read_input_tokens
    assert event["cache_read_input_tokens"] == call.cache_read_input_tokens
