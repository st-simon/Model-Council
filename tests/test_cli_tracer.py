from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from model_council.cli import app


def test_fixture_review_produces_a_persisted_report(tmp_path: Path) -> None:
    runner = CliRunner()
    fixture = Path(__file__).parent / "fixtures" / "single_review.yaml"

    result = runner.invoke(
        app,
        ["review", "--fixture", str(fixture), "--home", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    assert summary["state"] == "COMPLETED"
    assert summary["successful_reviewers"] == ["architect"]
    report = Path(summary["report_path"])
    assert report.exists()
    assert "architect" in report.read_text(encoding="utf-8")
    assert (tmp_path / "council.db").exists()
