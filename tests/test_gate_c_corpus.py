from __future__ import annotations

import hashlib
import json
from pathlib import Path

from model_council.configuration import ProviderConfig
from model_council.egress import EgressGuard
from model_council.models import PromptEnvelope

CORPUS_PATH = Path("tests/fixtures/gate_c_qwen_public_corpus.json")
CORPUS_SHA256 = "b75768802f6ae6a93829cdd035e5a8f1ace2294bc2400902d4944029ec32c9a0"
ENVELOPE_SHA256 = "7eb5638022bff718f1f9f70b59197c54dcdfb708178336f738f330de7524ee15"


def test_gate_c_public_corpus_is_frozen_and_passes_egress_scan() -> None:
    raw = CORPUS_PATH.read_bytes()
    payload = json.loads(raw)
    envelope = PromptEnvelope.model_validate(payload["review_envelope"])

    assert hashlib.sha256(raw).hexdigest() == CORPUS_SHA256
    assert envelope.envelope_hash == ENVELOPE_SHA256
    assert payload["data_class"] == "PUBLIC"
    assert payload["capability_probe"]["expected"] == {"status": "ok"}

    authorized = EgressGuard().authorize(
        envelope,
        "qwen_model_studio",
        ProviderConfig(network_enabled=True, allowed_data_classes=["PUBLIC"]),
    )
    assert authorized is envelope
