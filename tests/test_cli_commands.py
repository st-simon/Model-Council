from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from model_council.cli import app


def test_status_and_resume_read_the_persisted_run(tmp_path: Path) -> None:
    runner = CliRunner()
    fixture = Path(__file__).parent / "fixtures" / "single_review.yaml"
    review_result = runner.invoke(
        app,
        ["review", "--fixture", str(fixture), "--home", str(tmp_path)],
    )
    assert review_result.exit_code == 0, review_result.output

    status_result = runner.invoke(
        app,
        ["status", "R-TRACER-001", "--home", str(tmp_path)],
    )
    resume_result = runner.invoke(
        app,
        ["resume", "R-TRACER-001", "--home", str(tmp_path)],
    )

    assert status_result.exit_code == 0, status_result.output
    assert resume_result.exit_code == 0, resume_result.output
    assert json.loads(status_result.output)["state"] == "COMPLETED"
    assert json.loads(resume_result.output)["state"] == "COMPLETED"
