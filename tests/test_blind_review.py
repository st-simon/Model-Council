from __future__ import annotations

import asyncio
import json
from pathlib import Path

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.models import CallStatus, ReviewInput

REVIEWERS = [
    "fixture_qwen",
    "fixture_kimi",
    "fixture_grok",
    "fixture_glm",
]


def test_four_reviewers_are_blind_until_aggregation(tmp_path: Path) -> None:
    gateway = FixtureModelGateway()
    application = CouncilApplication(
        gateway=gateway,
        run_store=SQLiteRunStore(tmp_path / "council.db"),
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="blind-project",
        run_id="R-BLIND-001",
        proposal="Introduce a transactional order service.",
        context={"src/order.py": "update_order(); update_inventory()"},
        reviewers=REVIEWERS,
        minimum_successful_reviewers=3,
    )

    summary = asyncio.run(application.start_review(request))

    assert summary.state.value == "COMPLETED"
    assert summary.successful_reviewers == sorted(REVIEWERS)
    assert len(gateway.requests) == 4
    for captured in gateway.requests:
        serialized = captured.prompt + json.dumps(captured.context)
        peers = set(REVIEWERS) - {captured.role}
        assert all(peer not in serialized for peer in peers)


def test_one_reviewer_failure_completes_as_partial_when_quorum_holds(
    tmp_path: Path,
) -> None:
    gateway = FixtureModelGateway(behaviors={"fixture_grok": "fail"})
    application = CouncilApplication(
        gateway=gateway,
        run_store=SQLiteRunStore(tmp_path / "council.db"),
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="partial-project",
        run_id="R-PARTIAL-001",
        proposal="Introduce a transactional order service.",
        reviewers=REVIEWERS,
        minimum_successful_reviewers=3,
    )

    summary = asyncio.run(application.start_review(request))

    assert summary.state.value == "COMPLETED"
    assert summary.partial_review is True
    assert summary.failed_reviewers == ["fixture_grok"]
    assert summary.successful_reviewers == sorted(set(REVIEWERS) - {"fixture_grok"})


def test_invalid_output_is_repaired_once_before_acceptance(tmp_path: Path) -> None:
    gateway = FixtureModelGateway(behaviors={"fixture_kimi": "invalid_once"})
    application = CouncilApplication(
        gateway=gateway,
        run_store=SQLiteRunStore(tmp_path / "council.db"),
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="repair-project",
        run_id="R-REPAIR-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_kimi"],
        minimum_successful_reviewers=1,
    )

    summary = asyncio.run(application.start_review(request))

    assert summary.state.value == "COMPLETED"
    assert summary.successful_reviewers == ["fixture_kimi"]
    assert gateway.repair_attempts["fixture_kimi"] == 1


def test_invalid_output_is_marked_invalid_after_two_repairs(tmp_path: Path) -> None:
    gateway = FixtureModelGateway(behaviors={"fixture_kimi": "invalid_always"})
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=gateway,
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="invalid-project",
        run_id="R-INVALID-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_kimi"],
        minimum_successful_reviewers=1,
    )

    summary = asyncio.run(application.start_review(request))

    assert summary.state.value == "FAILED"
    assert gateway.repair_attempts["fixture_kimi"] == 2
    assert run_store.list_calls(request.run_id)[0].status == CallStatus.INVALID
