from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime

import httpx
import pytest

from model_council.adapters.qwen_tokens import QwenTemporaryKeyIssuer
from model_council.models import CallErrorKind, ModelCallError

NOW = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
TOKEN = "st-test-temporary-token"


def test_mint_uses_parent_only_for_the_fixed_900_second_token_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["method"] = request.method
        return httpx.Response(
            200,
            json={"token": TOKEN, "expires_at": int(NOW.timestamp()) + 900},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    issuer = QwenTemporaryKeyIssuer(client=client)
    try:
        result = asyncio.run(issuer.mint("parent-test-only", now=NOW))
    finally:
        asyncio.run(client.aclose())

    assert captured == {
        "url": "https://dashscope.aliyuncs.com/api/v1/tokens?expire_in_seconds=900",
        "authorization": "Bearer parent-test-only",
        "method": "POST",
    }
    assert result.token == TOKEN
    assert result.expires_at == datetime(2026, 8, 24, 0, 15, tzinfo=UTC)
    assert result.fingerprint == hashlib.sha256(TOKEN.encode()).hexdigest()
    assert TOKEN not in repr(result)
    assert "parent-test-only" not in repr(issuer)
    assert json.dumps(result.evidence(), sort_keys=True) == json.dumps(
        {
            "expires_at": "2026-08-24T00:15:00+00:00",
            "fingerprint_sha256": hashlib.sha256(TOKEN.encode()).hexdigest(),
        },
        sort_keys=True,
    )


def test_mint_gateway_never_passes_the_parent_key_to_the_model_adapter() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"token": TOKEN, "expires_at": int(NOW.timestamp()) + 900},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    issuer = QwenTemporaryKeyIssuer(client=client)
    try:
        gateway, minted = asyncio.run(
            issuer.mint_gateway(
                "parent-test-only",
                alias_to_model={"architect_primary_v1": "approved-model"},
                base_url=(
                    "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
                ),
                region="cn-beijing",
                now=NOW,
            )
        )
    finally:
        asyncio.run(client.aclose())

    assert gateway._api_key == TOKEN
    assert gateway._api_key != "parent-test-only"
    assert minted.token == TOKEN


def test_mint_failure_keeps_only_allowlisted_error_evidence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "code": "InvalidApiKey",
                "message": "secret-bearing provider detail must be discarded",
                "request_id": "902fee3b-f7f0-9a8c-96a1-6b4ea25af114",
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ModelCallError) as raised:
            asyncio.run(
                QwenTemporaryKeyIssuer(client=client).mint("parent-test-only", now=NOW)
            )
    finally:
        asyncio.run(client.aclose())

    error = raised.value
    assert error.code == "TEMPORARY_KEY_HTTP_401"
    assert error.kind == CallErrorKind.AUTHENTICATION
    assert error.provider_error_code == "InvalidApiKey"
    assert error.provider_request_id == "902fee3b-f7f0-9a8c-96a1-6b4ea25af114"
    assert "secret-bearing" not in str(error)
    assert "parent-test-only" not in repr(error)


def test_mint_failure_discards_unknown_code_and_unsafe_request_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "code": "../../not-allowlisted",
                "message": "discard me",
                "request_id": "unsafe request id",
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ModelCallError) as raised:
            asyncio.run(
                QwenTemporaryKeyIssuer(client=client).mint("parent-test-only", now=NOW)
            )
    finally:
        asyncio.run(client.aclose())

    assert raised.value.provider_error_code is None
    assert raised.value.provider_request_id is None


@pytest.mark.parametrize(
    "body",
    [
        {"token": TOKEN, "expires_at": int(NOW.timestamp()) + 900, "extra": True},
        {"token": "sk-not-temporary", "expires_at": int(NOW.timestamp()) + 900},
        {"token": TOKEN, "expires_at": int(NOW.timestamp()) + 901},
    ],
)
def test_mint_rejects_response_outside_the_approved_contract(
    body: dict[str, object],
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    )
    try:
        with pytest.raises(ModelCallError, match="TEMPORARY_KEY_INVALID_RESPONSE"):
            asyncio.run(
                QwenTemporaryKeyIssuer(client=client).mint("parent-test-only", now=NOW)
            )
    finally:
        asyncio.run(client.aclose())
