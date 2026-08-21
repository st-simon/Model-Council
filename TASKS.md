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

## Current milestone — Phase 2A verified

M2 — Provider verification and guarded live review. The independent proposal
`20260821-phase-2-provider-verification` received Gate A approval on 2026-08-21.
Phase 2A offline provider-readiness was verified on 2026-08-21. Do not install
provider dependencies, add a live adapter, use credentials, or allow provider
egress without the separate Gate B and Gate C approvals defined in the proposal.

- [x] Split role, logical-model, provider, and prompt configuration.
- [x] Add canonical versioned prompt envelopes and challenger output contract.
- [x] Persist logical calls separately from physical review/repair attempts.
- [x] Add retry classification, timeout preservation, and idempotent resume.
- [x] Add fail-closed secret/PII/injection scanning and guarded gateway seam.
- [x] Add offline `verify-models` capability verification.
- [x] Add cache-aware usage fields and atomic soft/hard budget foundations.
- [x] Add migration, contract, recovery, security, budget, and CLI tests.

## Blocking decisions for live-provider work

- Provider/data egress matrix
- Credential source and rotation expectations
- Per-run and global budget values
- Approved provider model aliases after `verify-models`
- First low-risk real test repository
