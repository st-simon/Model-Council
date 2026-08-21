from __future__ import annotations

import asyncio

from model_council.models import (
    CallErrorKind,
    Finding,
    GatewayRequest,
    GatewayResponse,
    ModelCallError,
    ProviderCapabilities,
    ReviewOutput,
)


class FixtureModelGateway:
    def __init__(self, behaviors: dict[str, str] | None = None) -> None:
        self.requests: list[GatewayRequest] = []
        self.behaviors = behaviors or {}
        self.repair_attempts: dict[str, int] = {}
        self.review_attempts: dict[str, int] = {}

    async def capabilities(self, model_alias: str) -> ProviderCapabilities:
        await asyncio.sleep(0)
        return ProviderCapabilities(
            provider="fixture",
            model_alias=model_alias,
            actual_model_id=f"{model_alias.replace('_', '-')}-v1",
            structured_output=True,
            prompt_cache=False,
            network_call_performed=False,
        )

    async def review(self, request: GatewayRequest) -> GatewayResponse:
        self.requests.append(request)
        previous_attempts = self.review_attempts.get(request.role, 0)
        self.review_attempts[request.role] = previous_attempts + 1
        await asyncio.sleep(0)
        behavior = self.behaviors.get(request.role)
        if behavior == "fail":
            raise ModelCallError("FIXTURE_PROVIDER_FAILURE")
        if behavior == "interrupt":
            raise RuntimeError("fixture process interrupted")
        if behavior == "transient_once" and previous_attempts == 0:
            raise ModelCallError("FIXTURE_TRANSIENT_FAILURE", CallErrorKind.TRANSIENT)
        if behavior in {"invalid_once", "invalid_always", "repair_transient_once"}:
            return self._response(request, "{invalid-json")
        return self._valid_response(request)

    async def repair(
        self, request: GatewayRequest, raw_output: str, validation_error: str
    ) -> GatewayResponse:
        previous_attempts = self.repair_attempts.get(request.role, 0)
        self.repair_attempts[request.role] = previous_attempts + 1
        await asyncio.sleep(0)
        if (
            self.behaviors.get(request.role) == "repair_transient_once"
            and previous_attempts == 0
        ):
            raise ModelCallError(
                "FIXTURE_REPAIR_TRANSIENT_FAILURE", CallErrorKind.TRANSIENT
            )
        if self.behaviors.get(request.role) == "invalid_always":
            return self._response(request, "{still-invalid")
        return self._valid_response(request)

    def _valid_response(self, request: GatewayRequest) -> GatewayResponse:
        output = ReviewOutput(
            reviewer=request.role,
            summary=f"{request.role} completed an offline fixture review.",
            findings=[
                Finding(
                    category="architecture",
                    raw_severity="P2",
                    claim="The proposal needs an explicit transaction invariant.",
                    recommendation="Document and test the atomic update boundary.",
                )
            ],
        )
        return self._response(request, output.model_dump_json())

    def _response(self, request: GatewayRequest, raw: str) -> GatewayResponse:
        input_tokens = len(request.prompt.split())
        cached = self.behaviors.get(request.role) == "cached"
        return GatewayResponse(
            raw_output=raw,
            provider="fixture",
            actual_model_id=(request.model_alias or request.role).replace("_", "-")
            + "-v1",
            input_tokens=input_tokens,
            uncached_input_tokens=0 if cached else input_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=input_tokens if cached else 0,
            output_tokens=len(raw.split()),
            latency_ms=0,
        )
