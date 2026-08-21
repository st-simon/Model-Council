from __future__ import annotations

from model_council.models import (
    GatewayRequest,
    GatewayResponse,
    ModelCallError,
    ProviderCapabilities,
)
from model_council.ports import ModelGateway


class RoutingModelGateway:
    def __init__(self, gateways: dict[str, ModelGateway]) -> None:
        self._gateways = gateways

    async def capabilities(self, model_alias: str) -> ProviderCapabilities:
        return await self._resolve(model_alias).capabilities(model_alias)

    async def review(self, request: GatewayRequest) -> GatewayResponse:
        alias = request.model_alias or request.role
        return await self._resolve(alias).review(request)

    async def repair(
        self, request: GatewayRequest, raw_output: str, validation_error: str
    ) -> GatewayResponse:
        alias = request.model_alias or request.role
        return await self._resolve(alias).repair(request, raw_output, validation_error)

    def _resolve(self, model_alias: str) -> ModelGateway:
        try:
            return self._gateways[model_alias]
        except KeyError as error:
            raise ModelCallError("MODEL_ALIAS_UNRESOLVED") from error
