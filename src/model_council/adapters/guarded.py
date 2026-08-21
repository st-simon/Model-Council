from __future__ import annotations

from model_council.configuration import ProviderConfig
from model_council.egress import EgressDenied, EgressGuard
from model_council.models import GatewayRequest, GatewayResponse, ProviderCapabilities
from model_council.ports import ModelGateway


class GuardedModelGateway:
    def __init__(
        self,
        delegate: ModelGateway,
        provider: str,
        policy: ProviderConfig,
        guard: EgressGuard,
    ) -> None:
        self.delegate = delegate
        self.provider = provider
        self.policy = policy
        self.guard = guard

    async def capabilities(self, model_alias: str) -> ProviderCapabilities:
        return await self.delegate.capabilities(model_alias)

    async def review(self, request: GatewayRequest) -> GatewayResponse:
        self._authorize(request)
        return await self.delegate.review(request)

    async def repair(
        self, request: GatewayRequest, raw_output: str, validation_error: str
    ) -> GatewayResponse:
        self._authorize(request)
        return await self.delegate.repair(request, raw_output, validation_error)

    def _authorize(self, request: GatewayRequest) -> None:
        if request.envelope is None:
            raise EgressDenied("PROMPT_ENVELOPE_REQUIRED")
        self.guard.authorize(request.envelope, self.provider, self.policy)
