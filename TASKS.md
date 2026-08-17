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

## Next milestone — not approved

M2 — Provider verification and guarded live review. Prepare a separate proposal
after the blocking decisions below are resolved; do not add provider egress on
the authority of Phase 1 approval.

## Blocking decisions for live-provider work

- Provider/data egress matrix
- Credential source and rotation expectations
- Per-run and global budget values
- Approved provider model aliases after `verify-models`
- First low-risk real test repository
