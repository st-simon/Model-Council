from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.qwen import QwenModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.gate_c import GateCRunner, GateCStopped
from model_council.models import CallStatus, RunState

ALIAS = "architect_primary_v1"
MODEL = "qwen3.7-max-2026-05-20"
BASE_URL = "https://workspace.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1"
CORPUS = Path("tests/fixtures/gate_c_qwen_public_corpus.json")
IN_WINDOW = datetime(2026, 8, 22, 1, 0, tzinfo=UTC)


def _provider_response(
    raw_output: str,
    request_id: str,
    *,
    model: str = MODEL,
    input_tokens: int = 20,
    output_tokens: int = 5,
) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"x-request-id": request_id},
        json={
            "model": model,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": raw_output},
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
            },
        },
    )


def _runner(
    tmp_path: Path, handler: httpx.MockTransport, *, now: datetime = IN_WINDOW
) -> tuple[GateCRunner, SQLiteRunStore, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=handler)
    gateway = QwenModelGateway(
        alias_to_model={ALIAS: MODEL},
        base_url=BASE_URL,
        api_key="test-only-key",
        client=client,
    )
    store = SQLiteRunStore(tmp_path / "council.db")
    return (
        GateCRunner(
            gateway=gateway,
            run_store=store,
            artifact_store=LocalArtifactStore(tmp_path),
            now=now,
        ),
        store,
        client,
    )


def test_gate_c_runs_probe_then_review_once_and_persists_evidence(
    tmp_path: Path,
) -> None:
    bodies: list[dict[str, object]] = []
    review = json.dumps(
        {
            "reviewer": "architect",
            "summary": "The bounded retry design preserves ambiguity safety.",
            "findings": [],
            "radical_challenges": [],
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if len(bodies) == 1:
            return _provider_response('{"status":"ok"}', "req-probe")
        return _provider_response(review, "req-review", input_tokens=80)

    runner, store, client = _runner(tmp_path, httpx.MockTransport(handler))
    try:
        result = asyncio.run(runner.execute(CORPUS))
    finally:
        asyncio.run(client.aclose())

    assert result.state == RunState.COMPLETED
    assert result.physical_requests == 2
    assert result.input_tokens == 100
    assert 0 < result.cost_rmb <= 0.20
    assert result.report_path.exists()
    assert len(bodies) == 2
    assert bodies[0]["max_completion_tokens"] == 256
    assert bodies[1]["max_completion_tokens"] == 1792
    assert all(body["enable_thinking"] is False for body in bodies)
    assert all(body["stream"] is False for body in bodies)
    calls = store.list_calls(result.run_id)
    assert [call.status for call in calls] == [
        CallStatus.SUCCEEDED,
        CallStatus.SUCCEEDED,
    ]
    assert len(store.list_attempts(result.run_id)) == 2


def test_gate_c_stops_after_invalid_probe_without_review(tmp_path: Path) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response('{"status":"wrong"}', "req-probe")

    runner, store, client = _runner(tmp_path, httpx.MockTransport(handler))
    try:
        with pytest.raises(GateCStopped, match="PROBE_INVALID"):
            asyncio.run(runner.execute(CORPUS))
    finally:
        asyncio.run(client.aclose())

    assert requests == 1
    assert store.load_state("R-GATE-C-QWEN-001") == RunState.FAILED
    calls = store.list_calls("R-GATE-C-QWEN-001")
    assert len(calls) == 1
    assert calls[0].status == CallStatus.INVALID


def test_gate_c_rejects_model_mismatch_as_invalid(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _provider_response(
            '{"status":"ok"}', "req-probe", model="qwen-unapproved"
        )

    runner, store, client = _runner(tmp_path, httpx.MockTransport(handler))
    try:
        with pytest.raises(GateCStopped, match="ACTUAL_MODEL_ID_MISMATCH"):
            asyncio.run(runner.execute(CORPUS))
    finally:
        asyncio.run(client.aclose())

    calls = store.list_calls("R-GATE-C-QWEN-001")
    assert calls[0].status == CallStatus.INVALID
    assert calls[0].error_code == "ACTUAL_MODEL_ID_MISMATCH"


@pytest.mark.parametrize(
    ("request_id", "cached_tokens", "error_code"),
    [
        (None, 0, "PROVIDER_REQUEST_ID_MISSING"),
        ("req-probe", 1, "CACHE_OBSERVED"),
    ],
)
def test_gate_c_rejects_missing_evidence_or_observed_cache(
    tmp_path: Path,
    request_id: str | None,
    cached_tokens: int,
    error_code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        headers = {"x-request-id": request_id} if request_id is not None else {}
        return httpx.Response(
            200,
            headers=headers,
            json={
                "model": MODEL,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"status":"ok"}'},
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 5,
                    "prompt_tokens_details": {"cached_tokens": cached_tokens},
                },
            },
        )

    runner, store, client = _runner(tmp_path, httpx.MockTransport(handler))
    try:
        with pytest.raises(GateCStopped, match=error_code):
            asyncio.run(runner.execute(CORPUS))
    finally:
        asyncio.run(client.aclose())

    calls = store.list_calls("R-GATE-C-QWEN-001")
    assert len(calls) == 1
    assert calls[0].status == CallStatus.INVALID
    assert calls[0].error_code == error_code


def test_gate_c_stops_after_invalid_provider_usage(tmp_path: Path) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response(
            '{"status":"ok"}',
            "req-probe",
            input_tokens=-1,
        )

    runner, store, client = _runner(tmp_path, httpx.MockTransport(handler))
    try:
        with pytest.raises(GateCStopped, match="PROVIDER_INVALID_RESPONSE"):
            asyncio.run(runner.execute(CORPUS))
    finally:
        asyncio.run(client.aclose())

    assert requests == 1
    assert store.load_state("R-GATE-C-QWEN-001") == RunState.FAILED
    calls = store.list_calls("R-GATE-C-QWEN-001")
    assert len(calls) == 1
    assert calls[0].status == CallStatus.FAILED_TERMINAL
    assert calls[0].error_code == "PROVIDER_INVALID_RESPONSE"


def test_gate_c_rejects_outside_window_before_any_provider_request(
    tmp_path: Path,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response('{"status":"ok"}', "req-probe")

    runner, _store, client = _runner(
        tmp_path,
        httpx.MockTransport(handler),
        now=datetime(2026, 8, 21, 0, 0, tzinfo=UTC),
    )
    try:
        with pytest.raises(GateCStopped, match="AUTHORIZATION_WINDOW_CLOSED"):
            asyncio.run(runner.execute(CORPUS))
    finally:
        asyncio.run(client.aclose())

    assert requests == 0
