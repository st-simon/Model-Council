# Model Council

Model Council is an auditable multi-model engineering review system. Four
read-only reviewer roles independently inspect a Codex proposal, structured
findings are normalized and reconciled, and Codex remains the only repository
write actor. High-impact unresolved decisions are escalated to the human
governor.

Status: **implementation preparation / proposal pending approval**.

Blueprint provenance: `MODEL_COUNCIL_BLUEPRINT_v0.2.md`, 1,833 lines,
SHA-256 `fba10c921eeaf0e6bce18b5b123294352e0748ceff880b53646362925cb8c7b5`.
The source attachment remains outside the repository; this project currently
stores the implementation interpretation, not a duplicate of the attachment.

## First reliable workflow

Given a normalized task, a Codex proposal, and a bounded project context, run
four blind reviewers through a replaceable model gateway, validate their
structured outputs, persist the recoverable run state, and produce an auditable
raw council report. Phase 1 proves this end to end with deterministic fixture
reviewers before any real provider call.

## Baseline and stack

- Workspace baselines: AI Agent or Workflow App + Python CLI or Automation
- Target runtime: Python `>=3.12,<3.14`
- Planned dependency manager: `uv` with `uv.lock` (not yet installed locally)
- Planned core: Typer, Pydantic v2, SQLAlchemy, Alembic, SQLite, Jinja2,
  `httpx`, `tenacity`, `orjson`, and a provider gateway adapter
- Deferred: Redis, PostgreSQL, Docker Compose, LangGraph, CrewAI, AutoGen,
  dashboard, and production deployment

The current development machine is an Apple M4 MacBook Pro with 16 GB memory,
macOS 15.0, Python 3.13.7, and Node 24.15.0. Provider credentials and verified
model slugs have not been inspected or configured.

## Documents

- [Project goal](docs/PROJECT_GOAL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation plan](IMPLEMENTATION_PLAN_v0.2.md)
- [Active proposal](proposals/active/20260818-model-council-mvp0.md)
- [Decisions](DECISIONS.md)
- [Tasks](TASKS.md)

## Setup and commands

No application dependencies or provider SDKs are installed yet. The approved
Phase 1 will add reproducible setup, run, and test commands. Until then:

```bash
git diff --check
```

Runtime data will default to `~/.model-council/` and must never be committed.
