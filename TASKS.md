# Tasks

## Current milestone

M0 — Blueprint v0.2 implementation preparation

- [x] Read and reconcile the full blueprint.
- [x] Establish project goal, baseline, architecture, and security boundary.
- [x] Select stable orchestration seams and compare alternatives.
- [x] Define phased implementation and Phase 1 acceptance criteria.
- [x] Create the active full proposal.
- [x] Human governor approved Phase 1 on 2026-08-18.

## Completed milestone

M1 — Offline blind-review kernel

- [x] Create `pyproject.toml`, package layout, and `uv.lock`.
- [x] Add one CLI smoke tracer and test.
- [x] Add schemas, transitions, and port contracts test-first.
- [x] Add deterministic fixture model gateway.
- [x] Add SQLite run store and migrations.
- [x] Add local artifact store and structured operational logging.
- [x] Expand from one reviewer to four isolated reviewers.
- [x] Add partial failure, schema repair, quorum, resume, and idempotency.
- [x] Export a raw council report and run full Phase 1 verification.

## Current milestone — Gate C blocked; temporary-key renewal implemented offline

M2 — Provider verification and guarded live review. The independent proposal
`20260821-phase-2-provider-verification` received Gate A approval on 2026-08-21.
Phase 2A offline provider-readiness was verified on 2026-08-21. Gate B was
approved on 2026-08-21 and the Qwen adapter was verified against mock transport.
Gate C and its three supplementary model-risk controls were approved on
2026-08-21. The unused Tokyo authorization was superseded on 2026-08-22 by an
approved Alibaba Cloud China Model Studio Beijing (`cn-beijing`) authorization.
The guarded runner made one terminal HTTP 403 probe on 2026-08-23, then stopped
without review or retry. That authorization is consumed. A replacement proposal
removes the IP allowlist and adds a 900-second temporary Key plus diagnostic and
evidence hardening. It was approved for implementation on 2026-08-23; renewed
live execution remains separately gated.

- [x] Split role, logical-model, provider, and prompt configuration.
- [x] Add canonical versioned prompt envelopes and challenger output contract.
- [x] Persist logical calls separately from physical review/repair attempts.
- [x] Add retry classification, timeout preservation, and idempotent resume.
- [x] Add fail-closed secret/PII/injection scanning and guarded gateway seam.
- [x] Add offline `verify-models` capability verification.
- [x] Add cache-aware usage fields and atomic soft/hard budget foundations.
- [x] Add migration, contract, recovery, security, budget, and CLI tests.
- [x] Record the Gate B Qwen/PUBLIC-only provider policy and its approved
  Beijing replacement.
- [x] Add and lock HTTPX as the reviewed direct transport.
- [x] Implement the Qwen adapter with sanitized error classification.
- [x] Verify the approved alias and capabilities without network or credentials.
- [x] Persist safe request IDs and pricing snapshot provenance.
- [x] Pass mock adapter, migration, regression, lint, format, and type checks.

## Gate C approved decisions

- Synthetic public corpus and exact permitted material
- Execution window and no-retry policy
- Maximum requests, attempts, tokens, planning ceiling, and RMB hard budget
- Credential and provider-console prerequisites
- Local evidence retention and Human Governor deletion ownership

## Gate C authorization preparation

- [x] Freeze a synthetic `PUBLIC` capability probe and review envelope.
- [x] Record raw corpus, envelope, and section hashes.
- [x] Define exact request, attempt, token, time, and spend ceilings.
- [x] Define endpoint, credential, console, stop, and retention conditions.
- [x] Add an offline corpus integrity and egress-scan test.
- [x] Preserve the unused Tokyo authorization as superseded.
- [x] Human Governor approval of
  `20260822-gate-c-qwen-beijing-live-verification`.
- [x] Restrict the adapter and guarded runner to `cn-beijing` and reject Tokyo.
- [x] Split JSON-mode, schema-enforcement, and local-validation capabilities.
- [x] Reject provider output extras and non-stop `finish_reason` values.
- [x] Implement and mock-test the two-request Gate C runner.
- [x] Harden provider usage invariants and reject inconsistent cache accounting.
- [x] Cover transport, finish reason, request ID, cache, repair, alias, envelope,
  egress-policy, and per-call attempt-ceiling boundaries.
- [x] Synchronize README and Security/Ops status language.
- [x] Execute one approved probe; stop terminally on HTTP 403.
- [ ] Confirm the failed dedicated Key was revoked or reset.
- [x] Approve
  `20260823-gate-c-qwen-beijing-temporary-key-renewal`.
- [x] Implement allowlisted provider error evidence and a safe Gate C evidence
  home.
- [x] Implement a 900-second temporary-Key mint boundary without exposing the
  parent Key to the model adapter.
- [x] Reconcile the abandoned local proxy-failure attempt to a documented
  terminal pre-provider failure without a network request.
- [ ] Clean-commit offline preflight before any renewed live execution.
- [ ] Separately approve the renewed implementation SHA.
