from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
import yaml

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.models import ReviewInput

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Model Council offline workflow commands."""


def _application(home: Path) -> CouncilApplication:
    return CouncilApplication(
        gateway=FixtureModelGateway(),
        run_store=SQLiteRunStore(home / "council.db"),
        artifact_store=LocalArtifactStore(home),
    )


@app.command()
def review(
    fixture: Annotated[Path, typer.Option(exists=True, readable=True)],
    home: Annotated[Path, typer.Option()],
) -> None:
    """Run an offline fixture-backed blind review."""
    payload = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    request = ReviewInput.model_validate(payload)
    summary = asyncio.run(_application(home).start_review(request))
    typer.echo(summary.model_dump_json())


@app.command()
def status(run_id: str, home: Annotated[Path, typer.Option()]) -> None:
    """Show the persisted state and report location for a run."""
    typer.echo(_application(home).status(run_id).model_dump_json())


@app.command()
def resume(run_id: str, home: Annotated[Path, typer.Option()]) -> None:
    """Resume an interrupted fixture-backed run."""
    typer.echo(asyncio.run(_application(home).resume(run_id)).model_dump_json())
