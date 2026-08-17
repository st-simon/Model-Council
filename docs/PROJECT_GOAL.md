# Project Goal

## Product objective

Build an auditable, resumable, and cost-aware engineering review system in
which independent model roles identify risks in a Codex proposal without
seeing one another's first-round output. Codex remains the sole implementation
actor, while the user governs material scope, data, budget, and high-impact
disputes.

## Target user

The initial user is the human governor operating Model Council locally across
software and AI projects. Team workflows, hosted multi-tenancy, and a public
service are not Phase 1 assumptions.

## First workflow that must be reliable

Input:

- a normalized task approval envelope;
- a Codex proposal;
- a deterministic, bounded context bundle;
- four configured reviewer roles.

Output:

- one recoverable run record;
- four isolated, schema-valid review records or explicit per-reviewer failure
  records;
- token/cost/latency call metadata;
- immutable prompt/context hashes and evidence artifacts;
- a raw council report that does not silently invent consensus.

## Phase 1 acceptance criteria

1. A fixture-backed CLI command completes an end-to-end four-role blind review
   without network access or credentials.
2. Reviewers receive no other reviewer's output before aggregation.
3. The same logical call key is not duplicated on resume.
4. One reviewer failure produces a partial run when the configured quorum is
   still satisfied.
5. Invalid structured output is retried through a bounded repair path and then
   recorded as invalid.
6. SQLite state and evidence exports can be inspected and reconciled.
7. Tests cover success, isolation, partial failure, schema failure,
   idempotency, and resume.

## Top constraints

1. Privacy and governance correctness
2. Auditability and recoverability
3. Review quality
4. Cost and latency
5. Implementation speed

## Explicitly deferred

- real provider calls and verified model slugs;
- semantic deduplication, embedding retrieval, debate, appeal, and escalation;
- Codex implementation automation against a target repository;
- scorecards, baseline experiments, shadow mode, dashboard, MCP, GitHub, and
  hosted deployment;
- reviewer shell, filesystem, repository-browse, or connector tools;
- Redis, PostgreSQL, containers, and distributed execution.

## Human-governed decisions before live-provider testing

- which project data may leave the machine;
- provider-by-provider source-code and PII policy;
- budget limits and pricing source;
- credential provisioning method;
- the first low-risk target project and its acceptance criteria.
