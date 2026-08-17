# Model Council v0.2 — Offline Blind-Review Kernel

- Proposal ID: `20260818-model-council-mvp0`
- Status: `proposed`
- Date: 2026-08-18
- Owner: Codex (Coordinator / Architect / Builder after approval)
- Human governor: user

## Background

The supplied `MODEL_COUNCIL_BLUEPRINT_v0.2.md` defines a multi-model,
blind-review engineering council with human escalation, Codex as the only write
actor, structured findings, recoverable state, bounded cost, and scorecards.
The project directory was empty and had no project governance or implementation
artifacts.

## Purpose

Approve the smallest implementation slice that can validate the architecture
without provider credentials, external data transfer, or commitment to a
specific model gateway.

## Scope

- Python CLI/package foundation with reproducible dependencies
- `CouncilApplication` orchestration interface
- injected `ModelGateway`, `RunStore`, and `ArtifactStore` ports
- deterministic fixture model gateway for four reviewer roles
- SQLite state, migrations, idempotent call claims, and resume
- local immutable evidence artifacts and raw report export
- Pydantic review/finding schemas and bounded repair behavior
- blind isolation, terminal barrier, partial-failure quorum
- structured operational logs with sanitized fields
- focused tests and golden fixtures

## Non-goals

- real provider calls, credential setup, or model slug selection
- source-code egress or approval of the blueprint's example provider matrix
- semantic dedup, debate, decision, appeal, escalation, scorecards, baseline,
  final audit, shadow mode, MCP, GitHub, dashboard, or deployment
- reviewer shell/filesystem tools or writes to a target repository
- Redis, PostgreSQL, containers, workflow frameworks, or distributed execution

## Proposed approach

Implement an offline vertical slice behind three ports. The application core
coordinates a run and enforces governance invariants. A fixture gateway returns
deterministic reviewer outputs; a SQLite adapter owns atomic run state; a local
artifact adapter writes immutable evidence snapshots. The CLI is only a caller
of the application interface.

The first tracer runs one fixture reviewer through the complete stack. After
that passes, expand the same path to four concurrent blind reviewers, then add
failure and resume behavior. No external provider package is needed for the
first passing slice.

## Alternatives considered

### Direct script pipeline

Rejected. Directly importing LiteLLM, SQLAlchemy, and filesystem functions into
stage scripts reduces initial files but makes retries, usage, idempotency, and
recovery knowledge leak across every caller.

### Full blueprint state machine and governance in one pass

Rejected for MVP-0. It delays the first verifiable output, multiplies migration
surface, and mixes deterministic core correctness with unresolved product and
provider policy.

### Event sourcing or workflow framework

Deferred. Replay benefits do not justify the additional concepts and
operations before local SQLite recovery has been tested on real runs.

## Implementation steps

1. Add package metadata, lock file, CLI smoke entry point, and smoke test.
2. Define domain schemas, run states, legal transitions, and typed failures.
3. Define ports and fixture adapters using dependency injection.
4. Complete the one-reviewer persistence/export tracer.
5. Add four-role blind fan-out and terminal barrier.
6. Add schema repair, partial failure, and quorum policy.
7. Add logical-call uniqueness, status, and resume.
8. Verify state/artifact/report reconciliation and logged-field privacy.

## Ownership and affected paths

- Codex owns project implementation paths after approval.
- Planned source: `src/model_council/`
- Planned migrations: `migrations/`
- Tests and fixtures: `tests/`
- Configuration and prompts: `config/`, `prompts/`
- Documentation: `README.md`, `docs/`, `DECISIONS.md`, `TASKS.md`
- Runtime data: outside the repo under `~/.model-council/`
- Target repositories: read-only and out of scope for this proposal

## Security/Ops classification

Required. This is an AI orchestration system that will later handle provider
credentials and potentially proprietary repository content. Phase 1 avoids
network egress and real credentials. It must still verify ignored secrets,
sanitized logs, untrusted-content boundaries, local artifact ownership, and a
default-deny future data policy.

## Risks and mitigations

- **Overbuilding before provider evidence** — use one offline vertical slice
  and defer integrations.
- **Adapter interface mirrors one provider** — define requests/results in
  project vocabulary and contract-test a fixture adapter first.
- **SQLite/artifact divergence** — SQLite owns structured truth; artifacts are
  immutable, content-addressed snapshots reconciled by IDs and hashes.
- **Blind-review leakage** — construct each request independently and assert
  no peer output appears before the aggregation barrier.
- **Duplicate calls on resume** — atomically claim a unique logical call key.
- **Sensitive content in logs** — log identifiers, hashes, counts, and
  sanitized errors; keep content in governed evidence artifacts.
- **Python/runtime drift** — declare `>=3.12,<3.14`, lock dependencies, and
  verify on the current Python 3.13 runtime.

## Validation plan

- Smoke: CLI starts and one fixture run completes.
- Unit: schemas, state transitions, call-key generation, quorum, repair limits.
- Integration: SQLite + artifact store + report reconciliation.
- Isolation: reviewer request snapshots contain no peer review output.
- Recovery: simulated interruption resumes without a duplicate logical call.
- Failure: one invalid/failed reviewer records a partial result under quorum.
- Hygiene: `git diff --check`, ignored secret/local-state paths, and no network
  required by default tests.

## Done criteria

All Phase 1 acceptance criteria in `docs/PROJECT_GOAL.md` pass from a clean
setup; setup/run/test commands are documented; no real secret or provider call
is needed; security/logging checks have no open P0/P1 issue; the proposal moves
through `approved -> in_progress -> implemented -> verified`.

## State transition plan

- Current: `proposed`
- On explicit approval: `approved`, then `in_progress` when code work begins
- After implementation: `implemented`
- After required verification: `verified`
- Archive only when Phase 1 has no open acceptance gap
- Use `blocked` if approval, environment setup, or a required security decision
  prevents progress

## Approval request

Approve this proposal to authorize Phase 1 only. Live provider setup and any
repository-content egress remain a separate approval boundary.
