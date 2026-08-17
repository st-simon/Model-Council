from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.models import InvalidStateTransition, ReviewInput, RunState


def test_run_transitions_are_validated_and_audited(tmp_path: Path) -> None:
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=FixtureModelGateway(),
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="state-project",
        run_id="R-STATE-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_qwen"],
        minimum_successful_reviewers=1,
    )

    asyncio.run(application.start_review(request))

    assert run_store.list_transitions(request.run_id) == [
        (RunState.INITIALIZED, RunState.BLIND_REVIEW_RUNNING),
        (RunState.BLIND_REVIEW_RUNNING, RunState.BLIND_REVIEW_DONE),
        (RunState.BLIND_REVIEW_DONE, RunState.COMPLETED),
    ]
    with pytest.raises(InvalidStateTransition):
        run_store.transition(request.run_id, RunState.BLIND_REVIEW_RUNNING)
