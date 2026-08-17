# Tasks

## Current milestone

M0 — Blueprint v0.2 implementation preparation

- [x] Read and reconcile the full blueprint.
- [x] Establish project goal, baseline, architecture, and security boundary.
- [x] Select stable orchestration seams and compare alternatives.
- [x] Define phased implementation and Phase 1 acceptance criteria.
- [x] Create the active full proposal.
- [ ] Human governor approves or revises the active proposal.

## Next milestone after approval

M1 — Offline blind-review kernel

- [ ] Create `pyproject.toml`, package layout, and `uv.lock`.
- [ ] Add one CLI smoke tracer and test.
- [ ] Add schemas, transitions, and port contracts test-first.
- [ ] Add deterministic fixture model gateway.
- [ ] Add SQLite run store and migrations.
- [ ] Add local artifact store and structured operational logging.
- [ ] Expand from one reviewer to four isolated reviewers.
- [ ] Add partial failure, schema repair, quorum, resume, and idempotency.
- [ ] Export a raw council report and run full Phase 1 verification.

## Blocking decisions for live-provider work

- Provider/data egress matrix
- Credential source and rotation expectations
- Per-run and global budget values
- Approved provider model aliases after `verify-models`
- First low-risk real test repository
