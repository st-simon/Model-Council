# Model Council Implementation Plan v0.2

Status: proposed on 2026-08-18. No application code, dependencies, credentials,
or provider calls are authorized by this document alone.

## Delivery strategy

Build one recoverable vertical slice at a time. Each phase must leave a runnable
system, focused verification, documented failure behavior, and a reversible
change. The sequence intentionally separates deterministic workflow
correctness from external model quality and data-egress decisions.

## Phase 1 — Offline blind-review kernel

Purpose: prove that the system can run, isolate, persist, fail partially, and
resume without network access.

Deliverables:

1. Reproducible Python package and lock file.
2. Domain types for run, call, review, finding, usage, and typed failures.
3. `CouncilApplication` with `start_review`, `resume`, and `status`.
4. `ModelGateway`, `RunStore`, and `ArtifactStore` ports.
5. Deterministic four-role fixture gateway.
6. SQLite/Alembic run store and local artifact store.
7. Minimal state transition policy and logical-call uniqueness.
8. Pydantic structured-output validation plus two bounded repair attempts.
9. Blind concurrent fan-out, terminal-state barrier, and configurable quorum.
10. Raw report export and structured JSON operational logs.
11. CLI: `council review --fixture`, `status`, and `resume`.
12. Focused tests and a versioned golden fixture set.

Done when all acceptance criteria in `docs/PROJECT_GOAL.md` pass from a clean
local setup and no test requires a provider credential.

## Phase 2 — Provider verification and guarded live review

Purpose: connect one provider at a time without weakening data or domain
boundaries.

Deliverables:

- models/roles configuration split and prompt templates;
- `council verify-models` capability probes and basic test calls;
- provider adapter(s), timeouts, retries, and sanitized errors;
- secret/PII/injection scan pipeline and default-deny provider data policy;
- pre-call and post-call token/cost accounting;
- soft/hard run budget behavior;
- explicit fixture-to-live contract tests.

Entry gate: human approval of the provider/data matrix, credential mechanism,
budget, and first low-risk test corpus.

## Phase 3 — Governance and finding lifecycle

Purpose: turn raw reviews into governed, traceable decisions.

Deliverables:

- finding registry and evidence anchors;
- deterministic severity normalization;
- conservative exact/candidate dedup with ambiguous items kept separate;
- disagreement detection and one bounded anonymous rebuttal round;
- Codex ACCEPT/MODIFY/REJECT/DEFER/UNCERTAIN decisions;
- P0/P1 appeal rules and 3–5 item human escalation packets;
- DEFER revisit conditions and expiry;
- audit-fix convergence limit.

Entry gate: Phase 2 security tests and at least one successful low-risk live run.

## Phase 4 — Context, evaluation, and adaptive membership

Purpose: prove the council's incremental value rather than assuming it.

Deliverables:

- git-aware deterministic context builder and per-role budgets;
- reviewer, Codex-decision, and human-burden scorecards;
- Codex self-review baselines;
- shadow reviewer mode and periodic membership review;
- final-audit routing rules.

Entry gate: enough labeled runs to evaluate acceptance, false-positive, escape,
cost, and latency metrics.

## Phase 5 — Optional integrations

MCP, GitHub PRs, dashboards, hosted APIs, PostgreSQL, Redis, containers, and
distributed execution are separate proposals. They require demonstrated load
or workflow value and their own security/operations plan.

## Phase 1 build order

1. Package/CLI smoke tracer.
2. Schemas and transition-policy unit tests.
3. Ports plus fixture adapters.
4. Start one role, persist it, and export one result.
5. Expand to four-role blind fan-out and barrier.
6. Add failure, quorum, schema repair, and budget-free usage metadata.
7. Add resume/idempotency tests.
8. Reconcile SQLite state, artifacts, logs, and report.
9. Run clean-environment verification and security review of logged fields.

Do not begin the next numbered step while the current tracer fails.

## First real test project

Select a low-risk repository with a small database, a simple frontend/backend
path, explicit acceptance criteria, and tests capable of confirming at least
some findings. Use a frozen commit and a bounded context manifest. Do not use
credentials, customer data, or production write access.

## Verification commands planned for Phase 1

```bash
uv sync --locked
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run council review --fixture tests/fixtures/sample_review.yaml
```

These commands become authoritative only after the Phase 1 package is created.
