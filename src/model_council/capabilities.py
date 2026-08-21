from __future__ import annotations

from model_council.configuration import RuntimeConfig
from model_council.models import ModelVerification
from model_council.ports import ModelGateway


async def verify_configured_models(
    config: RuntimeConfig, gateway: ModelGateway
) -> list[ModelVerification]:
    results: list[ModelVerification] = []
    for alias, configured in sorted(config.models.items()):
        observed = await gateway.capabilities(alias)
        missing = [
            capability
            for capability, required in configured.required_capabilities.items()
            if required and not bool(getattr(observed, capability, False))
        ]
        if observed.actual_model_id != configured.model:
            missing.append("actual_model_id")
        results.append(
            ModelVerification(
                model_alias=alias,
                provider=observed.provider,
                actual_model_id=observed.actual_model_id,
                compatible=not missing and observed.provider == configured.provider,
                missing_capabilities=missing,
                network_call_performed=observed.network_call_performed,
            )
        )
    return results
