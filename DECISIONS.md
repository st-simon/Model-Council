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

## D-006 — Canonical prompt envelope and guarded egress

- Status: accepted under Phase 2 Gate A
- Decision: separate static prompt, approved project context, dynamic payload,
  and policy metadata in a canonical hashed envelope. Any future outbound adapter
  must sit behind a fail-closed `EgressGuard`.
- Reason: prompt caching and provider formatting may vary, but data authorization
  and audit identity must remain provider-neutral and independently testable.

## D-007 — Logical calls and physical attempts

- Status: accepted under Phase 2 Gate A
- Decision: retain one logical call identity while persisting every review or
  repair transport attempt as a child record with its own status and usage.
- Reason: a timeout, transient failure, schema repair, and successful review have
  different retry and billing implications; collapsing them loses recovery truth.
- Alternative deferred: a Saga or workflow engine remains unjustified for the
  single-host SQLite v0.x runtime.

## D-008 — Capability-gated caching and atomic budget reservations

- Status: accepted under Phase 2 Gate A
- Decision: cache behavior is an observed provider capability, never a mandatory
  correctness dependency. Reserve estimated call cost atomically before starting
  concurrent work and record cache read/write/uncached usage separately.
- Reason: provider support and pricing vary, while hard-budget safety must not
  depend on concurrent calls finishing in a favorable order.

## D-009 — First provider adapter and Gate B boundary

- Status: accepted under Phase 2 Gate B on 2026-08-21
- Decision: implement one direct HTTPX adapter for Alibaba Cloud Model Studio in
  the Tokyo region. Map logical alias `architect_primary_v1` to pinned model
  `qwen3.7-max-2026-05-20`; permit only `PUBLIC` egress; keep provider inference
  logging and prompt caching disabled.
- Credential boundary: read a dedicated, model/IP-scoped key only from
  `DASHSCOPE_API_KEY` and the workspace ID only from
  `DASHSCOPE_WORKSPACE_ID` after Gate C. Rotate at least every 90 days and reset,
  disable, or delete immediately on suspected exposure.
- Data handling assumption: the provider states call data is not used for model
  training; payload retention remains unknown, so non-public data stays denied.
- Reason: a direct adapter keeps provider schema, timeout, usage, and sanitized
  error mapping behind `ModelGateway` without introducing a multi-provider SDK.
- Gate boundary: Gate B authorizes offline adapter implementation and mock
  verification only. Credentials, network enablement, content egress, and billed
  calls still require Gate C.
