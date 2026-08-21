# Model Council

Model Council is an auditable multi-model engineering review system. Four
read-only reviewer roles independently inspect a Codex proposal, structured
findings are normalized and reconciled, and Codex remains the only repository
write actor. High-impact unresolved decisions are escalated to the human
governor.

Status: **Phase 1 verified; Phase 2B Qwen adapter verified offline**.

Blueprint provenance: `MODEL_COUNCIL_BLUEPRINT_v0.2.md`, 1,833 lines,
SHA-256 `fba10c921eeaf0e6bce18b5b123294352e0748ceff880b53646362925cb8c7b5`.
The source attachment remains outside the repository; this project currently
stores the implementation interpretation, not a duplicate of the attachment.

## First reliable workflow

Given a normalized task, a Codex proposal, and a bounded project context, run
four blind reviewers through a replaceable model gateway, validate their
structured outputs, persist the recoverable run state, and produce an auditable
raw council report. Phase 1 proves this end to end with deterministic fixture
reviewers. Phase 2A adds provider-neutral prompt envelopes, offline capability
verification, fail-closed egress policy, physical call attempts, retry recovery,
cache-aware usage fields, and atomic budget reservations without making a real
provider call. Phase 2B adds one Qwen Model Studio adapter for the Tokyo region,
with mock-transport contract tests and an offline capability declaration. It is
not wired into the review command and remains network-disabled pending Gate C.

## Baseline and stack

- Workspace baselines: AI Agent or Workflow App + Python CLI or Automation
- Target runtime: Python `>=3.12,<3.14`
- Dependency manager: `uv` with committed `uv.lock`
- Phase 1 core: Typer, Pydantic v2, SQLAlchemy, Alembic, SQLite, PyYAML,
  `asyncio`, and `orjson`
- Phase 2B transport: HTTPX `0.28.x`, used only by the Qwen adapter
- Deferred: Redis, PostgreSQL, Docker Compose, LangGraph, CrewAI, AutoGen,
  dashboard, and production deployment

The current development machine is an Apple M4 MacBook Pro with 16 GB memory,
macOS 15.0, Python 3.13.7, and Node 24.15.0. Provider credentials and verified
model slugs have not been inspected or configured.

## Documents

- [Project goal](docs/PROJECT_GOAL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation plan](IMPLEMENTATION_PLAN_v0.2.md)
- [Verified Phase 1 proposal](proposals/archive/20260818-model-council-mvp0.md)
- [Active Phase 2 proposal](proposals/active/20260821-phase-2-provider-verification.md)
- [Security boundary](docs/SECURITY.md)
- [Decisions](DECISIONS.md)
- [Tasks](TASKS.md)

## Setup and commands

Install `uv`, then create the locked development environment:

```bash
uv sync --locked --all-groups
```

Run the four-reviewer offline example:

```bash
uv run council review \
  --fixture examples/offline-review.yaml \
  --home .model-council
uv run council status R-OFFLINE-SAMPLE-001 --home .model-council
uv run council resume R-OFFLINE-SAMPLE-001 --home .model-council
```

Verify configured logical aliases through offline capability declarations:

```bash
uv run council verify-models --config-dir config
```

Verify the project:

```bash
uv lock --check
uv run ruff check .
uv run mypy src
uv run pytest -q
```

The CLI requires an explicit `--home`; local examples use `.model-council/`,
which is ignored. The checked-in Qwen provider policy allows only `PUBLIC` data
and has `network_enabled: false`. `verify-models` does not read credentials or
make provider calls. Gate C is still required before supplying credentials,
enabling the provider, transmitting content, or incurring cost.
