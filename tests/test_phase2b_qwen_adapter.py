from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from model_council.adapters.qwen import PRICING_SNAPSHOT_ID, QwenModelGateway
from model_council.models import (
    AttemptKind,
    CallErrorKind,
    GatewayRequest,
    ModelCallError,
    PolicyMetadata,
    PromptEnvelope,
    ReviewInput,
)

ALIAS = "architect_primary_v1"
MODEL = "qwen3.7-max-2026-05-20"
BASE_URL = "https://workspace.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1"


def _request() -> GatewayRequest:
    envelope = PromptEnvelope(
        static_prefix="Review evidence and return JSON only.",
        project_context={"README.md": "Public fixture content."},
        dynamic_payload="Review the proposal.",
        policy_metadata=PolicyMetadata(
            data_class="PUBLIC",
            provider_policy_version="qwen-tokyo-public-v1",
            prompt_version="architect-v1",
        ),
    )
    return GatewayRequest(
        project_id="public-fixture",
        run_id="R-QWEN-MOCK-001",
        role="architect",
        model_alias=ALIAS,
        prompt="not used by the adapter",
        context=envelope.project_context,
        envelope=envelope,
        max_output_tokens=2048,
    )


def _gateway(
    handler: httpx.MockTransport,
) -> tuple[QwenModelGateway, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=handler)
    return (
        QwenModelGateway(
            alias_to_model={ALIAS: MODEL},
            base_url=BASE_URL,
            api_key="test-only-key",
            client=client,
        ),
        client,
    )


def test_capabilities_are_declared_without_a_network_call() -> None:
    gateway = QwenModelGateway(
        alias_to_model={ALIAS: MODEL}, base_url=BASE_URL, api_key=None
    )

    result = asyncio.run(gateway.capabilities(ALIAS))

    assert result.actual_model_id == MODEL
    assert result.structured_output is True
    assert result.usage_reporting is True
    assert result.request_id_reporting is True
    assert result.region == "ap-northeast-1"
    assert result.network_call_performed is False


def test_review_maps_openai_compatible_response_without_cache_assumptions() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"x-request-id": "req-safe-123"},
            json={
                "id": "chatcmpl-fallback",
                "model": MODEL,
                "choices": [{"message": {"content": '{"summary":"ok"}'}}],
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 15,
                    "prompt_tokens_details": {"cached_tokens": 20},
                },
            },
        )

    gateway, client = _gateway(httpx.MockTransport(handler))
    try:
        result = asyncio.run(gateway.review(_request()))
    finally:
        asyncio.run(client.aclose())

    assert captured["url"] == f"{BASE_URL}/chat/completions"
    assert captured["authorization"] == "Bearer test-only-key"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == MODEL
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_completion_tokens"] == 2048
    assert "Public fixture content." in body["messages"][1]["content"]
    assert result.input_tokens == 120
    assert result.uncached_input_tokens == 100
    assert result.cache_read_input_tokens == 20
    assert result.cache_creation_input_tokens is None
    assert result.provider_request_id == "req-safe-123"
    assert result.pricing_snapshot_id == PRICING_SNAPSHOT_ID
    assert result.cost_rmb is None


@pytest.mark.parametrize(
    ("status", "kind", "retryable"),
    [
        (401, CallErrorKind.AUTHENTICATION, False),
        (429, CallErrorKind.THROTTLED, True),
        (500, CallErrorKind.TRANSIENT, True),
        (400, CallErrorKind.INVALID_REQUEST, False),
    ],
)
def test_http_errors_are_sanitized_and_classified(
    status: int, kind: CallErrorKind, retryable: bool
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="secret provider response body")

    gateway, client = _gateway(httpx.MockTransport(handler))
    try:
        with pytest.raises(ModelCallError) as caught:
            asyncio.run(gateway.review(_request()))
    finally:
        asyncio.run(client.aclose())

    assert caught.value.code == f"PROVIDER_HTTP_{status}"
    assert caught.value.kind == kind
    assert caught.value.retryable is retryable
    assert "secret provider response body" not in str(caught.value)


def test_missing_credential_fails_before_transport() -> None:
    gateway = QwenModelGateway(
        alias_to_model={ALIAS: MODEL}, base_url=BASE_URL, api_key=None
    )

    with pytest.raises(ModelCallError, match="PROVIDER_CREDENTIAL_MISSING") as caught:
        asyncio.run(gateway.review(_request()))

    assert caught.value.kind == CallErrorKind.AUTHENTICATION


def test_adapter_rejects_unapproved_endpoint() -> None:
    with pytest.raises(ValueError, match="approved Tokyo"):
        QwenModelGateway(
            alias_to_model={ALIAS: MODEL},
            base_url="https://example.com/compatible-mode/v1",
            api_key=None,
        )


def test_unsafe_provider_request_id_is_not_persisted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"x-request-id": "unsafe request id"},
            json={
                "model": MODEL,
                "choices": [{"message": {"content": '{"summary":"ok"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    gateway, client = _gateway(httpx.MockTransport(handler))
    try:
        response = asyncio.run(gateway.review(_request()))
    finally:
        asyncio.run(client.aclose())

    assert response.provider_request_id is None


def test_malformed_provider_response_is_terminal_and_sanitized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "private content"})

    gateway, client = _gateway(httpx.MockTransport(handler))
    try:
        with pytest.raises(ModelCallError) as caught:
            asyncio.run(gateway.review(_request()))
    finally:
        asyncio.run(client.aclose())

    assert caught.value.code == "PROVIDER_INVALID_RESPONSE"
    assert caught.value.kind == CallErrorKind.INVALID_RESPONSE
    assert "private content" not in str(caught.value)


def test_provider_evidence_is_persisted_on_physical_attempt(tmp_path) -> None:
    from model_council.adapters.sqlite import SQLiteRunStore

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"x-request-id": "req-persisted"},
            json={
                "id": "chatcmpl-persisted",
                "model": MODEL,
                "choices": [{"message": {"content": '{"summary":"ok"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    gateway, client = _gateway(httpx.MockTransport(handler))
    store = SQLiteRunStore(tmp_path / "council.db")
    review_input = ReviewInput(
        project_id="public-fixture",
        run_id="R-QWEN-PERSIST-001",
        proposal="Review public evidence.",
        reviewers=["architect"],
    )
    store.create_or_load(review_input)
    request = _request().model_copy(update={"run_id": review_input.run_id})
    assert request.envelope is not None
    store.claim_call(
        review_input.run_id,
        request.role,
        ALIAS,
        request.envelope.context_hash,
        request.envelope.envelope_hash,
    )
    attempt = store.start_attempt(review_input.run_id, request.role, AttemptKind.REVIEW)
    try:
        response = asyncio.run(gateway.review(request))
    finally:
        asyncio.run(client.aclose())
    store.finish_attempt_success(attempt.attempt_id, response)

    persisted = store.list_attempts(review_input.run_id)[0]
    assert persisted.provider_request_id == "req-persisted"
    assert persisted.pricing_snapshot_id == PRICING_SNAPSHOT_ID
    assert persisted.cost_rmb is None
