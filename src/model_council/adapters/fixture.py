from __future__ import annotations

import asyncio

from model_council.models import (
    Finding,
    GatewayRequest,
    GatewayResponse,
    ModelCallError,
    ReviewOutput,
)


class FixtureModelGateway:
    def __init__(self, behaviors: dict[str, str] | None = None) -> None:
        self.requests: list[GatewayRequest] = []
        self.behaviors = behaviors or {}
        self.repair_attempts: dict[str, int] = {}

    async def review(self, request: GatewayRequest) -> GatewayResponse:
        self.requests.append(request)
        await asyncio.sleep(0)
        behavior = self.behaviors.get(request.role)
        if behavior == "fail":
            raise ModelCallError("FIXTURE_PROVIDER_FAILURE")
        if behavior == "interrupt":
            raise RuntimeError("fixture process interrupted")
        if behavior in {"invalid_once", "invalid_always"}:
            return self._response(request, "{invalid-json")
        return self._valid_response(request)

    async def repair(
        self, request: GatewayRequest, raw_output: str, validation_error: str
    ) -> GatewayResponse:
        previous_attempts = self.repair_attempts.get(request.role, 0)
        self.repair_attempts[request.role] = previous_attempts + 1
        await asyncio.sleep(0)
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

    @staticmethod
    def _response(request: GatewayRequest, raw: str) -> GatewayResponse:
        return GatewayResponse(
            raw_output=raw,
            provider="fixture",
            actual_model_id=request.role,
            input_tokens=len(request.prompt.split()),
            output_tokens=len(raw.split()),
            latency_ms=0,
        )
