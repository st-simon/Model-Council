from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
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
from model_council.gate_c import (
    AUTHORIZATION_ID,
    MODEL_ALIAS,
    MODEL_ID,
    WINDOW_END,
    WINDOW_START,
    GateCRunner,
    GateCStopped,
    load_gate_c_corpus,
)
from model_council.models import ReviewInput
from model_council.ports import ModelGateway
from model_council.prompting import PromptBuilder

app = typer.Typer(no_args_is_help=True)
SAFE_WORKSPACE_ID = re.compile(r"^[A-Za-z0-9-]{1,100}$")
FULL_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
GATE_C_ENDPOINT_TEMPLATE = (
    "https://{workspace_id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)


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


def _gate_c_git_preflight(repo_root: Path, approved_commit: str) -> None:
    if FULL_COMMIT_SHA.fullmatch(approved_commit) is None:
        raise GateCStopped("APPROVED_COMMIT_MUST_BE_FULL_SHA")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != approved_commit:
        raise GateCStopped("HEAD_NOT_APPROVED_COMMIT")
    worktree = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if worktree:
        raise GateCStopped("WORKTREE_NOT_CLEAN")


def _gate_c_config_preflight(config_dir: Path) -> tuple[str, str]:
    config = load_runtime_config(config_dir)
    model = config.resolve_model(MODEL_ALIAS)
    provider = config.resolve_provider("qwen_model_studio")
    required_capabilities = {
        "json_mode": True,
        "local_schema_validation": True,
        "usage_reporting": True,
        "request_id_reporting": True,
    }
    if (
        model.model != MODEL_ID
        or model.provider != "qwen_model_studio"
        or model.required_capabilities != required_capabilities
    ):
        raise GateCStopped("APPROVED_MODEL_CONFIG_CHANGED")
    if (
        provider.network_enabled
        or provider.allowed_data_classes != ["PUBLIC"]
        or provider.region != "cn-beijing"
        or provider.endpoint_template != GATE_C_ENDPOINT_TEMPLATE
        or provider.credential_env != "DASHSCOPE_API_KEY"
        or provider.workspace_id_env != "DASHSCOPE_WORKSPACE_ID"
        or provider.training_use != "provider_states_not_used_for_training"
        or provider.payload_retention != "unknown"
        or provider.inference_logging_enabled
        or provider.prompt_cache_enabled
    ):
        raise GateCStopped("APPROVED_PROVIDER_CONFIG_CHANGED")
    return provider.endpoint_template, provider.region


@app.command("gate-c-qwen")
def gate_c_qwen(
    home: Annotated[Path, typer.Option()],
    approved_commit: Annotated[str, typer.Option()],
    authorization_id: Annotated[str, typer.Option()],
    execute: Annotated[bool, typer.Option()] = False,
    confirm_key_scoped: Annotated[bool, typer.Option()] = False,
    confirm_inference_logging_disabled: Annotated[bool, typer.Option()] = False,
    confirm_billing_access: Annotated[bool, typer.Option()] = False,
    confirm_offline_suite_passed: Annotated[bool, typer.Option()] = False,
    corpus: Annotated[
        Path, typer.Option(exists=True, readable=True, dir_okay=False)
    ] = Path("tests/fixtures/gate_c_qwen_public_corpus.json"),
    config_dir: Annotated[
        Path, typer.Option(exists=True, file_okay=False, readable=True)
    ] = Path("config"),
) -> None:
    """Execute the approved, two-request Qwen Beijing Gate C run."""
    now = datetime.now(UTC)
    confirmations = (
        confirm_key_scoped
        and confirm_inference_logging_disabled
        and confirm_billing_access
        and confirm_offline_suite_passed
    )
    if authorization_id != AUTHORIZATION_ID:
        raise typer.BadParameter("authorization ID does not match Gate C approval")
    if not execute:
        raise typer.BadParameter("--execute is required")
    if not confirmations:
        raise typer.BadParameter("all Gate C confirmations are required")
    if not WINDOW_START <= now <= WINDOW_END:
        raise typer.BadParameter("Gate C authorization window is closed")

    repo_root = config_dir.resolve().parent
    try:
        _gate_c_git_preflight(repo_root, approved_commit)
    except (GateCStopped, subprocess.CalledProcessError) as error:
        raise typer.BadParameter(f"Git preflight failed: {error}") from None

    try:
        endpoint_template, region = _gate_c_config_preflight(config_dir)
        load_gate_c_corpus(corpus)
    except GateCStopped as error:
        raise typer.BadParameter(f"Policy preflight failed: {error}") from None
    preflight_path = home / "gate-c-preflight.json"
    if preflight_path.exists():
        raise typer.BadParameter("Gate C home already contains a preflight record")
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    workspace_id = os.environ.get("DASHSCOPE_WORKSPACE_ID")
    if not api_key:
        raise typer.BadParameter("DASHSCOPE_API_KEY is missing")
    if not workspace_id or SAFE_WORKSPACE_ID.fullmatch(workspace_id) is None:
        raise typer.BadParameter("DASHSCOPE_WORKSPACE_ID is missing or invalid")
    endpoint = endpoint_template.format(workspace_id=workspace_id)
    gateway = QwenModelGateway(
        alias_to_model={MODEL_ALIAS: MODEL_ID},
        base_url=endpoint,
        api_key=api_key,
        region=region,
    )
    home.mkdir(parents=True, exist_ok=True)
    endpoint_hash = hashlib.sha256(endpoint.encode()).hexdigest()
    with preflight_path.open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "authorization_id": AUTHORIZATION_ID,
                    "approved_commit": approved_commit,
                    "checked_at": now.isoformat(),
                    "endpoint_sha256": endpoint_hash,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    runner = GateCRunner(
        gateway=gateway,
        run_store=SQLiteRunStore(home / "council.db"),
        artifact_store=LocalArtifactStore(home),
        now=now,
    )
    try:
        result = asyncio.run(runner.execute(corpus))
    except GateCStopped as error:
        typer.echo(f"Gate C stopped: {error}", err=True)
        typer.echo("Revoke or delete the Gate C API key now.", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(result.model_dump_json())
    typer.echo("Revoke or delete the Gate C API key now.", err=True)
