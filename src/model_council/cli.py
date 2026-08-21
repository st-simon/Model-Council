from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
import yaml

from model_council.adapters.artifacts import LocalArtifactStore
from model_council.adapters.fixture import FixtureModelGateway
from model_council.adapters.qwen import QwenModelGateway
from model_council.adapters.routing import RoutingModelGateway
from model_council.adapters.sqlite import SQLiteRunStore
from model_council.application import CouncilApplication
from model_council.capabilities import verify_configured_models
from model_council.configuration import load_runtime_config
from model_council.models import ReviewInput
from model_council.ports import ModelGateway
from model_council.prompting import PromptBuilder

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Model Council offline workflow commands."""


def _application(home: Path, config_dir: Path) -> CouncilApplication:
    config = load_runtime_config(config_dir)
    return CouncilApplication(
        gateway=FixtureModelGateway(),
        run_store=SQLiteRunStore(home / "council.db"),
        artifact_store=LocalArtifactStore(home),
        prompt_builder=PromptBuilder(
            config=config,
            prompt_dir=config_dir.parent / "prompts",
        ),
    )


def _offline_capability_gateway(config_dir: Path) -> RoutingModelGateway:
    config = load_runtime_config(config_dir)
    fixture = FixtureModelGateway()
    qwen_models = {
        alias: model.model
        for alias, model in config.models.items()
        if model.provider == "qwen_model_studio"
    }
    qwen_policy = config.resolve_provider("qwen_model_studio")
    qwen = QwenModelGateway(
        alias_to_model=qwen_models,
        base_url=qwen_policy.endpoint_template or "",
        api_key=None,
        region=qwen_policy.region or "",
    )
    gateways: dict[str, ModelGateway] = {}
    for alias, model in config.models.items():
        if model.provider == "fixture":
            gateways[alias] = fixture
        elif model.provider == "qwen_model_studio":
            gateways[alias] = qwen
        else:
            raise ValueError(
                f"unsupported provider in offline verifier: {model.provider}"
            )
    return RoutingModelGateway(gateways)


@app.command()
def review(
    fixture: Annotated[Path, typer.Option(exists=True, readable=True)],
    home: Annotated[Path, typer.Option()],
    config_dir: Annotated[
        Path, typer.Option(exists=True, file_okay=False, readable=True)
    ] = Path("config"),
) -> None:
    """Run an offline fixture-backed blind review."""
    payload = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    request = ReviewInput.model_validate(payload)
    summary = asyncio.run(_application(home, config_dir).start_review(request))
    typer.echo(summary.model_dump_json())


@app.command()
def status(
    run_id: str,
    home: Annotated[Path, typer.Option()],
    config_dir: Annotated[
        Path, typer.Option(exists=True, file_okay=False, readable=True)
    ] = Path("config"),
) -> None:
    """Show the persisted state and report location for a run."""
    typer.echo(_application(home, config_dir).status(run_id).model_dump_json())


@app.command()
def resume(
    run_id: str,
    home: Annotated[Path, typer.Option()],
    config_dir: Annotated[
        Path, typer.Option(exists=True, file_okay=False, readable=True)
    ] = Path("config"),
) -> None:
    """Resume an interrupted fixture-backed run."""
    typer.echo(
        asyncio.run(_application(home, config_dir).resume(run_id)).model_dump_json()
    )


@app.command("verify-models")
def verify_models(
    config_dir: Annotated[
        Path, typer.Option(exists=True, file_okay=False, readable=True)
    ] = Path("config"),
) -> None:
    """Verify configured aliases without credentials or provider calls."""
    config = load_runtime_config(config_dir)
    gateway = _offline_capability_gateway(config_dir)
    results = asyncio.run(verify_configured_models(config, gateway))
    typer.echo(
        json.dumps(
            [result.model_dump(mode="json") for result in results],
            ensure_ascii=False,
        )
    )
