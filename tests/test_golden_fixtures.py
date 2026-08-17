from __future__ import annotations

import asyncio
import json
from pathlib import Path

from model_council.adapters.fixture import FixtureModelGateway
from model_council.models import GatewayRequest, ReviewOutput


def test_fixture_review_contract_matches_the_golden_set() -> None:
    golden_path = Path(__file__).parent / "golden" / "fixture_reviews.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    gateway = FixtureModelGateway()

    for role, expected in golden.items():
        response = asyncio.run(
            gateway.review(
                GatewayRequest(
                    project_id="golden-project",
                    run_id="R-GOLDEN-001",
                    role=role,
                    prompt="Review a transaction proposal.",
                    context={},
                )
            )
        )
        output = ReviewOutput.model_validate_json(response.raw_output)
        assert output.model_dump() == expected
