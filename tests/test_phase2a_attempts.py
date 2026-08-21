from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.models import AttemptStatus, CallStatus, ReviewInput, RunState


def test_transient_failure_is_retried_without_repeating_successes(
    tmp_path: Path,
) -> None:
    gateway = FixtureModelGateway(behaviors={"fixture_qwen": "transient_once"})
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=gateway,
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="retry-project",
        run_id="R-RETRY-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_qwen"],
        minimum_successful_reviewers=1,
        max_provider_attempts=2,
    )

    first = asyncio.run(application.start_review(request))
    assert first.state == RunState.BLIND_REVIEW_RUNNING
    assert run_store.list_calls(request.run_id)[0].status == CallStatus.RETRY_WAIT

    resumed = asyncio.run(application.resume(request.run_id))

    assert resumed.state == RunState.COMPLETED
    assert len(gateway.requests) == 2
    assert [attempt.status for attempt in run_store.list_attempts(request.run_id)] == [
        AttemptStatus.RETRY_WAIT,
        AttemptStatus.SUCCEEDED,
    ]


def test_interrupted_attempt_is_preserved_as_timed_out_on_resume(
    tmp_path: Path,
) -> None:
    run_store = SQLiteRunStore(tmp_path / "council.db")
    artifacts = LocalArtifactStore(tmp_path)
    request = ReviewInput(
        project_id="interrupted-project",
        run_id="R-INTERRUPTED-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_qwen"],
        minimum_successful_reviewers=1,
        max_provider_attempts=2,
    )
    interrupted = CouncilApplication(
        gateway=FixtureModelGateway(behaviors={"fixture_qwen": "interrupt"}),
        run_store=run_store,
        artifact_store=artifacts,
    )

    with pytest.raises(RuntimeError, match="fixture process interrupted"):
        asyncio.run(interrupted.start_review(request))

    resumed = CouncilApplication(
        gateway=FixtureModelGateway(),
        run_store=run_store,
        artifact_store=artifacts,
    )
    summary = asyncio.run(resumed.resume(request.run_id))

    assert summary.state == RunState.COMPLETED
    assert [attempt.status for attempt in run_store.list_attempts(request.run_id)] == [
        AttemptStatus.TIMED_OUT,
        AttemptStatus.SUCCEEDED,
    ]


def test_transient_schema_repair_failure_resumes_the_logical_call(
    tmp_path: Path,
) -> None:
    gateway = FixtureModelGateway(behaviors={"fixture_qwen": "repair_transient_once"})
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=gateway,
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="repair-retry-project",
        run_id="R-REPAIR-RETRY-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_qwen"],
        max_provider_attempts=2,
    )

    first = asyncio.run(application.start_review(request))
    assert first.state == RunState.BLIND_REVIEW_RUNNING

    resumed = asyncio.run(application.resume(request.run_id))

    assert resumed.state == RunState.COMPLETED
    assert [attempt.status for attempt in run_store.list_attempts(request.run_id)] == [
        AttemptStatus.SUCCEEDED,
        AttemptStatus.RETRY_WAIT,
        AttemptStatus.SUCCEEDED,
        AttemptStatus.SUCCEEDED,
    ]
