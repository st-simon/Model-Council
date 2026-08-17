from __future__ import annotations

import pytest
from pydantic import ValidationError

from model_council.models import ReviewInput


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("project_id", "../../outside"),
        ("run_id", "runs/escape"),
        ("reviewers", ["../fixture_qwen"]),
    ],
)
def test_runtime_identifiers_reject_path_traversal(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "project_id": "safe-project",
        "run_id": "R-SAFE-001",
        "proposal": "Review a safe proposal.",
        "reviewers": ["fixture_qwen"],
        "minimum_successful_reviewers": 1,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        ReviewInput.model_validate(payload)
