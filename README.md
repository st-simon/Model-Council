# Model Council

Model Council is an auditable multi-model engineering review system. Four
read-only reviewer roles independently inspect a Codex proposal, structured
findings are normalized and reconciled, and Codex remains the only repository
write actor. High-impact unresolved decisions are escalated to the human
governor.

Status: **Phase 1 verified; the first Beijing Gate C authorization is blocked
after one terminal HTTP 403 probe; its temporary-key renewal is implemented
offline but no renewed live request is authorized**.

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
provider call. Phase 2B adds one Qwen Model Studio adapter for the Alibaba Cloud
China Model Studio Beijing region (`cn-beijing`), with mock-transport contract
tests and an offline capability declaration. It is
not wired into the general review command. Gate C adds a separate, fail-closed
two-request runner for the frozen synthetic public corpus. Checked-in provider
policy remains network-disabled; live execution requires the exact approval ID,
a clean approved commit, the authorized window, console confirmations, and
ephemeral environment credentials. The model adapter accepts only the Beijing
workspace endpoint and rejects Tokyo or generic DashScope model endpoints. The
renewed runner mints one 900-second temporary Key from a parent Key that never
enters the model adapter.

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
macOS 15.0, Python 3.13.7, and Node 24.15.0. Provider credential values have not
been inspected or recorded by this implementation session.

## Documents

- [Project goal](docs/PROJECT_GOAL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation plan](IMPLEMENTATION_PLAN_v0.2.md)
- [Verified Phase 1 proposal](proposals/archive/20260818-model-council-mvp0.md)
- [Active Phase 2 proposal](proposals/active/20260821-phase-2-provider-verification.md)
- [Approved Beijing Gate C authorization](proposals/active/20260822-gate-c-qwen-beijing-live-verification.md)
- [Approved temporary-key Gate C renewal](proposals/active/20260823-gate-c-qwen-beijing-temporary-key-renewal.md)
- [Superseded Tokyo Gate C authorization](proposals/active/20260821-gate-c-qwen-live-verification.md)
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

The previous authorization was consumed by one terminal HTTP 403 probe. Do not
resume its run or reuse its Key. The replacement command now requires
`DASHSCOPE_PARENT_API_KEY`, `DASHSCOPE_WORKSPACE_ID`, the exact Clash proxy route
at `127.0.0.1:7897`, a new evidence home, all console confirmations, and a
separately approved clean full commit SHA. The parent Key is used only for one
temporary-token request; only the returned 900-second Key reaches the model
adapter. Implementation does not itself authorize that request.

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
make provider calls. The Gate C runner uses an ephemeral Beijing-only in-memory
allow policy; it does not change the checked-in default. On 2026-08-23 one
approved probe reached the provider and returned terminal HTTP 403. No review or
retry followed. The consumed authorization cannot be reused. The earlier local
proxy-failure database has been reconciled to `FAILED` with
`LOCAL_PROXY_PREFLIGHT_FAILED` and no provider evidence.
