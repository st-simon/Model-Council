from __future__ import annotations

import asyncio
import json
from pathlib import Path

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.models import ReviewInput


def test_call_log_is_structured_and_excludes_prompt_content(tmp_path: Path) -> None:
    secret_sentinel = "PRIVATE-PROPOSAL-SENTINEL"
    run_store = SQLiteRunStore(tmp_path / "council.db")
    application = CouncilApplication(
        gateway=FixtureModelGateway(),
        run_store=run_store,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="log-project",
        run_id="R-LOG-001",
        proposal=secret_sentinel,
        context={"private.py": secret_sentinel},
        reviewers=["fixture_qwen"],
        minimum_successful_reviewers=1,
    )

    asyncio.run(application.start_review(request))

    log_path = tmp_path / "logs" / "council.jsonl"
    event = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["run_id"] == request.run_id
    assert event["role"] == "fixture_qwen"
    assert event["model_alias"] == "fixture_qwen"
    assert event["provider"] == "fixture"
    assert event["status"] == "SUCCEEDED"
    assert event["input_tokens"] > 0
    assert len(event["prompt_hash"]) == 64
    assert len(event["context_hash"]) == 64
    assert secret_sentinel not in log_path.read_text(encoding="utf-8")
    stored_call = run_store.list_calls(request.run_id)[0]
    assert stored_call.provider == "fixture"
    assert stored_call.actual_model_id == "fixture-qwen-v1"
    assert stored_call.input_tokens is not None and stored_call.input_tokens > 0
    assert stored_call.output_tokens is not None and stored_call.output_tokens > 0
    assert stored_call.cost_rmb == 0.0
    assert len(stored_call.prompt_hash) == 64
    assert len(stored_call.context_hash) == 64


def test_schema_repair_keeps_each_raw_response_attempt(tmp_path: Path) -> None:
    application = CouncilApplication(
        gateway=FixtureModelGateway(behaviors={"fixture_kimi": "invalid_once"}),
        run_store=SQLiteRunStore(tmp_path / "council.db"),
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ReviewInput(
        project_id="artifact-project",
        run_id="R-ARTIFACT-001",
        proposal="Introduce a transactional order service.",
        reviewers=["fixture_kimi"],
        minimum_successful_reviewers=1,
    )

    asyncio.run(application.start_review(request))

    call_dir = (
        tmp_path
        / "runs"
        / request.project_id
        / request.run_id
        / "calls"
        / "fixture_kimi"
    )
    attempts = sorted(call_dir.glob("raw-response-*.json"))
    assert [path.name for path in attempts] == [
        "raw-response-0.json",
        "raw-response-1.json",
    ]
    assert attempts[0].read_text(encoding="utf-8").startswith("{invalid-json")
    assert '"reviewer":"fixture_kimi"' in attempts[1].read_text(encoding="utf-8")
