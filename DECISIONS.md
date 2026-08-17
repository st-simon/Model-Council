# Decisions

## D-001 — Project baseline

- Status: accepted for preparation
- Decision: apply the AI Agent or Workflow App baseline plus Python CLI or
  Automation.
- Reason: the product is both an LLM orchestration workflow and a local CLI.

## D-002 — Stable orchestration seams

- Status: accepted
- Decision: keep the application core behind three injected ports:
  `ModelGateway`, `RunStore`, and `ArtifactStore`.
- Reason: provider, persistence, and export variability should not leak into
  orchestration or governance rules.
- Alternative rejected: stage functions directly importing LiteLLM and sharing
  a SQLAlchemy session. It is initially shorter but spreads retries, billing,
  idempotency, and persistence knowledge across callers.
- Alternative deferred: event sourcing. It offers excellent replay but adds
  migration and operational complexity before there is evidence it is needed.

## D-003 — Offline-first Phase 1

- Status: accepted
- Decision: use deterministic fixture model adapters for the first vertical
  slice; connect real providers only after the contracts, isolation tests, and
  fail-closed data boundary are verified.
- Reason: this separates core correctness from credentials, pricing, network
  behavior, and provider-specific schema quirks.

## D-004 — Structured source of truth

- Status: accepted
- Decision: SQLite is the v0.x structured source of truth. Rendered prompts,
  raw responses, Markdown, and JSON are immutable evidence snapshots/exports.
- Reason: this avoids dual-write ambiguity while keeping runs auditable.

## D-005 — Provider data policy defaults

- Status: accepted
- Decision: default-deny source-code transmission until the human governor
  approves the provider matrix. Credentials and detected secrets are always
  denied; scanner failure blocks egress.
- Reason: the example provider matrix in the blueprint is not authorization.
