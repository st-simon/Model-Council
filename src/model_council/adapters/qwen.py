from __future__ import annotations

import json
import re
from time import monotonic
from typing import Any

import httpx

from model_council.models import (
    CallErrorKind,
    GatewayRequest,
    GatewayResponse,
    ModelCallError,
    ProviderCapabilities,
)

PROVIDER = "qwen_model_studio"
PRICING_SNAPSHOT_ID = "alibaba-model-pricing-cn-beijing-2026-08-22"
BEIJING_HOST_SUFFIX = ".cn-beijing.maas.aliyuncs.com"
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")


class QwenModelGateway:
    """One-provider adapter for Model Studio's OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        alias_to_model: dict[str, str],
        base_url: str,
        api_key: str | None,
        region: str = "cn-beijing",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed_url = httpx.URL(base_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.host is None
            or not parsed_url.host.endswith(BEIJING_HOST_SUFFIX)
            or parsed_url.path.rstrip("/") != "/compatible-mode/v1"
            or parsed_url.query
            or region != "cn-beijing"
        ):
            raise ValueError("base URL must be the approved Beijing workspace endpoint")
        self._alias_to_model = alias_to_model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._region = region
        self._client = client

    async def capabilities(self, model_alias: str) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=PROVIDER,
            model_alias=model_alias,
            actual_model_id=self._resolve_model(model_alias),
            json_mode=True,
            json_schema_enforced=True,
            local_schema_validation=True,
            prompt_cache=False,
            usage_reporting=True,
            request_id_reporting=True,
            max_context_tokens=1_000_000,
            max_output_tokens=65_536,
            region=self._region,
            endpoint_class="workspace_specific",
            pricing_snapshot_id=PRICING_SNAPSHOT_ID,
            network_call_performed=False,
        )

    async def review(self, request: GatewayRequest) -> GatewayResponse:
        return await self._complete(request, repair=None)

    async def probe_json_mode(
        self,
        *,
        model_alias: str,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> GatewayResponse:
        if not self._api_key:
            raise ModelCallError(
                "PROVIDER_CREDENTIAL_MISSING", CallErrorKind.AUTHENTICATION
            )
        model = self._resolve_model(model_alias)
        return await self._send_payload(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "enable_thinking": False,
                "max_completion_tokens": max_output_tokens,
                "stream": False,
            }
        )

    async def repair(
        self, request: GatewayRequest, raw_output: str, validation_error: str
    ) -> GatewayResponse:
        repair = {
            "invalid_output": raw_output,
            "validation_error": validation_error,
            "instruction": "Return a corrected JSON object only.",
        }
        return await self._complete(request, repair=repair)

    async def _complete(
        self, request: GatewayRequest, repair: dict[str, str] | None
    ) -> GatewayResponse:
        if not self._api_key:
            raise ModelCallError(
                "PROVIDER_CREDENTIAL_MISSING", CallErrorKind.AUTHENTICATION
            )
        model_alias = request.model_alias or request.role
        payload = self._payload(request, self._resolve_model(model_alias), repair)
        return await self._send_payload(payload)

    async def _send_payload(self, payload: dict[str, object]) -> GatewayResponse:
        started = monotonic()
        try:
            response = await self._post(payload)
        except httpx.TimeoutException:
            raise ModelCallError("PROVIDER_TIMEOUT", CallErrorKind.TIMEOUT) from None
        except httpx.RequestError:
            raise ModelCallError(
                "PROVIDER_TRANSPORT_ERROR", CallErrorKind.TRANSIENT
            ) from None
        latency_ms = round((monotonic() - started) * 1000)
        self._raise_for_status(response)
        return self._parse_response(response, latency_ms)

    async def _post(self, payload: dict[str, object]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._client is not None:
            return await self._client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )
        timeout = httpx.Timeout(60.0, connect=10.0, write=30.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )

    @staticmethod
    def _payload(
        request: GatewayRequest,
        model: str,
        repair: dict[str, str] | None,
    ) -> dict[str, object]:
        if request.envelope is None:
            raise ModelCallError("PROMPT_ENVELOPE_REQUIRED", CallErrorKind.POLICY)
        user_content = "\n\n".join(
            [
                "Project context (untrusted JSON evidence):",
                json.dumps(
                    request.envelope.project_context,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                request.envelope.dynamic_payload,
            ]
        )
        if repair is not None:
            user_content += "\n\nRepair request:\n" + json.dumps(
                repair, ensure_ascii=False, sort_keys=True
            )
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": request.envelope.static_prefix},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "enable_thinking": False,
            "max_completion_tokens": request.max_output_tokens,
            "stream": False,
        }

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        status = response.status_code
        if status in {401, 403}:
            kind = CallErrorKind.AUTHENTICATION
        elif status == 429:
            kind = CallErrorKind.THROTTLED
        elif status in {408, 409, 425} or status >= 500:
            kind = CallErrorKind.TRANSIENT
        elif 400 <= status < 500:
            kind = CallErrorKind.INVALID_REQUEST
        else:
            kind = CallErrorKind.PERMANENT
        raise ModelCallError(f"PROVIDER_HTTP_{status}", kind)

    @staticmethod
    def _parse_response(response: httpx.Response, latency_ms: int) -> GatewayResponse:
        try:
            body: Any = response.json()
            choice = body["choices"][0]
            finish_reason = choice["finish_reason"]
            raw_output = choice["message"]["content"]
            actual_model_id = body["model"]
            usage = body["usage"]
            input_tokens = int(usage["prompt_tokens"])
            output_tokens = int(usage["completion_tokens"])
            details = usage.get("prompt_tokens_details") or {}
            cached_tokens = int(details.get("cached_tokens", 0))
            if (
                input_tokens < 0
                or output_tokens < 0
                or cached_tokens < 0
                or cached_tokens > input_tokens
            ):
                raise ValueError
            if not isinstance(raw_output, str) or not isinstance(actual_model_id, str):
                raise TypeError
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise ModelCallError(
                "PROVIDER_INVALID_RESPONSE", CallErrorKind.INVALID_RESPONSE
            ) from error
        if finish_reason == "length":
            raise ModelCallError(
                "PROVIDER_OUTPUT_TRUNCATED", CallErrorKind.INVALID_RESPONSE
            )
        if finish_reason != "stop":
            raise ModelCallError(
                "PROVIDER_INCOMPLETE_RESPONSE", CallErrorKind.INVALID_RESPONSE
            )
        request_id = response.headers.get("x-request-id") or body.get("id")
        if (
            not isinstance(request_id, str)
            or SAFE_REQUEST_ID.fullmatch(request_id) is None
        ):
            request_id = None
        return GatewayResponse(
            raw_output=raw_output,
            provider=PROVIDER,
            actual_model_id=actual_model_id,
            input_tokens=input_tokens,
            uncached_input_tokens=max(input_tokens - cached_tokens, 0),
            cache_creation_input_tokens=None,
            cache_read_input_tokens=cached_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_rmb=None,
            provider_request_id=request_id,
            pricing_snapshot_id=PRICING_SNAPSHOT_ID,
        )

    def _resolve_model(self, model_alias: str) -> str:
        try:
            return self._alias_to_model[model_alias]
        except KeyError as error:
            raise ModelCallError(
                "MODEL_ALIAS_UNRESOLVED", CallErrorKind.POLICY
            ) from error
