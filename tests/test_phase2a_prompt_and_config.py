from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from model_council.configuration import load_runtime_config
from model_council.models import (
    PolicyMetadata,
    PromptEnvelope,
    RadicalChallenge,
    ReviewInput,
)
from model_council.prompting import PromptBuilder


def test_prompt_envelope_hashes_sections_deterministically() -> None:
    first = PromptEnvelope(
        static_prefix="Review as an isolated architect.",
        project_context={"b.py": "b()", "a.py": "a()"},
        dynamic_payload="Proposal: add a transaction.",
        policy_metadata=PolicyMetadata(
            data_class="PUBLIC",
            provider_policy_version="offline-v1",
            prompt_version="architect-v1",
        ),
    )
    reordered = first.model_copy(
        update={"project_context": {"a.py": "a()", "b.py": "b()"}}
    )
    changed_task = first.model_copy(
        update={"dynamic_payload": "Proposal: add an idempotency key."}
    )

    assert first.section_hashes == reordered.section_hashes
    assert first.envelope_hash == reordered.envelope_hash
    assert first.static_hash == changed_task.static_hash
    assert first.dynamic_hash != changed_task.dynamic_hash
    assert first.envelope_hash != changed_task.envelope_hash


def test_runtime_config_separates_role_alias_and_provider() -> None:
    config = load_runtime_config(Path("config"))

    challenger = config.resolve_role("challenger")

    assert challenger.model_alias == "fixture_grok"
    assert challenger.prompt_version == "challenger-v1"
    assert config.resolve_model(challenger.model_alias).provider == "fixture"
    assert config.resolve_provider("fixture").network_enabled is False


def test_gate_b_qwen_policy_remains_offline_and_public_only() -> None:
    config = load_runtime_config(Path("config"))

    model = config.resolve_model("architect_primary_v1")
    provider = config.resolve_provider(model.provider)

    assert model.model == "qwen3.7-max-2026-05-20"
    assert model.required_capabilities == {
        "structured_output": True,
        "usage_reporting": True,
        "request_id_reporting": True,
    }
    assert provider.region == "ap-northeast-1"
    assert provider.allowed_data_classes == ["PUBLIC"]
    assert provider.network_enabled is False
    assert provider.payload_retention == "unknown"
    assert provider.inference_logging_enabled is False
    assert provider.prompt_cache_enabled is False


def test_radical_challenge_requires_falsification_fields() -> None:
    with pytest.raises(ValidationError):
        RadicalChallenge.model_validate(
            {
                "evidence": "The transaction premise is contradicted by the schema.",
                "minimal_alternative": "Use the existing unit-of-work boundary.",
                "trade_off": "Less flexibility.",
            }
        )

    challenge = RadicalChallenge(
        evidence="The transaction premise is contradicted by the schema.",
        minimal_alternative="Use the existing unit-of-work boundary.",
        trade_off="Less flexibility.",
        residual_risk="The existing boundary may still be too broad.",
    )
    assert challenge.residual_risk.startswith("The existing")


def test_prompt_builder_resolves_role_to_logical_alias_and_template() -> None:
    config = load_runtime_config(Path("config"))
    builder = PromptBuilder(config=config, prompt_dir=Path("prompts"))
    request = ReviewInput(
        project_id="prompt-project",
        run_id="R-PROMPT-001",
        proposal="Add a transaction.",
        reviewers=["architect"],
    )

    gateway_request = builder.build(request, "architect")

    assert gateway_request.model_alias == "fixture_qwen"
    assert "architecture reviewer" in gateway_request.prompt
    assert gateway_request.envelope is not None
    assert gateway_request.envelope.policy_metadata.prompt_version == "architect-v1"
