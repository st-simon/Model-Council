from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.models import ReviewInput


def test_resume_reuses_the_logical_call_after_process_interruption(
    tmp_path: Path,
) -> None:
    run_store = SQLiteRunStore(tmp_path / "council.db")
    artifacts = LocalArtifactStore(tmp_path)
    interrupted_gateway = FixtureModelGateway(behaviors={"fixture_qwen": "interrupt"})
    request = ReviewInput(
        project_id="resume-project",
        run_id="R-RESUME-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_qwen"],
        minimum_successful_reviewers=1,
    )
    interrupted_application = CouncilApplication(
        gateway=interrupted_gateway,
        run_store=run_store,
        artifact_store=artifacts,
    )

    with pytest.raises(RuntimeError, match="fixture process interrupted"):
        asyncio.run(interrupted_application.start_review(request))

    resumed_gateway = FixtureModelGateway()
    resumed_application = CouncilApplication(
        gateway=resumed_gateway,
        run_store=run_store,
        artifact_store=artifacts,
    )
    summary = asyncio.run(resumed_application.resume(request.run_id))

    assert summary.state.value == "COMPLETED"
    assert len(run_store.list_calls(request.run_id)) == 1
    assert len(interrupted_gateway.requests) == 1
    assert len(resumed_gateway.requests) == 1
