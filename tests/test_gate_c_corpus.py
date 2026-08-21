from __future__ import annotations

import hashlib
import json
from pathlib import Path

from model_council.configuration import ProviderConfig
from model_council.egress import EgressGuard
from model_council.models import PromptEnvelope

CORPUS_PATH = Path("tests/fixtures/gate_c_qwen_public_corpus.json")
CORPUS_SHA256 = "5733080e2e3453bfa4520be507309529774acee9bacc1ccfeff967a0c6b10bad"
ENVELOPE_SHA256 = "5d559b9159da3e6943a872e72cea6feff10cfa2800b9cf54e4d555ded5165734"


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
