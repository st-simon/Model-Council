# Architecture

## Product priority

Phase 1 is a thin offline vertical slice: normalized inputs enter a council run,
four fixture reviewer calls execute concurrently and blindly, validated results
are persisted, and a raw report is exported. It proves orchestration,
isolation, schema boundaries, persistence, observability, and resume before
provider variability is introduced.

## Environment summary

- Host: Apple M4 MacBook Pro, 16 GB memory, macOS 15.0
- Available runtime: Python 3.13.7; target range `>=3.12,<3.14`
- Node: 24.15.0 (not required for Phase 1)
- Local model server: Ollama executable present; installed model inventory was
  not available from the restricted inspection and is not required by Phase 1
- Planned package manager: `uv`; not currently installed
- Disk headroom observed: about 219 GiB
- Provider credentials, quotas, model slugs, and contracts: intentionally not
  inspected at preparation time

## System boundary

```text
CLI / future Codex tool
        |
        v
CouncilApplication  -- governance and orchestration policy
   |          |          |
   v          v          v
ModelGateway RunStore ArtifactStore
   |          |          |
fixture/      SQLite     local evidence tree
provider      adapter    and report exporter
adapters
```

The application core owns state-transition rules, blind fan-out, quorum,
budget checks, schema handling, and result aggregation. Adapters own network,
database, and filesystem mechanics.

## Public application interface

The narrow caller-facing interface should be equivalent to:

```python
class CouncilApplication:
    async def start_review(self, request: ReviewRequest) -> RunSummary: ...
    async def resume(self, run_id: RunId) -> RunSummary: ...
    def status(self, run_id: RunId) -> RunSummary: ...
```

The composition root supplies `ModelGateway`, `RunStore`, `ArtifactStore`, a
clock, and an ID generator. Tests use the same application interface as the
CLI.

## Required ports

### ModelGateway

Responsibilities: verify an alias, execute one structured review request,
return usage/latency/provider identity, and expose typed transient/permanent
failures. It must not decide workflow state or write artifacts.

### RunStore

Responsibilities: atomic state transitions, logical-call claiming,
idempotency, review/failure persistence, and resume snapshots. It hides
SQLAlchemy and SQLite from the application core.

### ArtifactStore

Responsibilities: immutable rendered prompt, context, raw response, and report
snapshots addressed by run/call identity and content hashes. It is not the
structured source of truth.

## Alternatives and trade-offs

### Selected: orchestration core with injected ports

- Small stable application surface
- Provider and persistence behavior are replaceable and testable
- Governance logic stays local to one module
- Slightly more upfront contract design

### Rejected: script pipeline with direct imports

- Fastest demo
- Couples every stage to LiteLLM, SQLAlchemy, filesystem layout, and retry
  semantics
- Resume and idempotency become cross-cutting and hard to verify

### Deferred: event-sourced workflow engine

- Best replay and audit semantics
- Excessive surface area, migrations, and operational concepts for v0.x
- Revisit only if SQLite snapshots cannot support real recovery cases

## Core invariants

- Only transitions allowed by the state policy may be persisted.
- A logical call key is unique for
  `(run_id, stage, model_alias, context_hash, prompt_hash)`.
- Blind-review input never includes another reviewer's output.
- Aggregation begins only after each role reaches a terminal call state.
- Scanner or policy uncertainty blocks external egress.
- Hard-budget exhaustion starts no new model call and preserves partial state.
- Reports never become an independent writable source of truth.
- Reviewer adapters cannot write a reviewed target repository.

## State model

The blueprint's complete state list remains the target vocabulary. Phase 1
implements only states exercised by its workflow, while storing state values in
an extensible form and rejecting unknown transitions. Later phases add task
approval, disagreement/debate, decisions, appeals, human pause, final audit,
and scoring without rewriting persistence.

## Model policy

Business code binds roles to logical aliases only. `models.yaml` maps aliases to
provider model slugs that must be populated and checked by `verify-models`.
`roles.yaml` binds role, prompt version, context budget, and alias.

Phase 1 uses `fixture_qwen`, `fixture_kimi`, `fixture_grok`, and `fixture_glm`.
The first real-provider phase must benchmark the real review workload and
record actual model ID, capabilities, pricing snapshot, prompt hash, context
hash, usage, latency, and fallback path for every call. Cross-provider fallback
is disabled until the data policy permits both sides of the fallback.

## Data and security boundary

Repository content is untrusted evidence. Context collection is followed by
secret scanning, PII classification, injection heuristics, provider policy,
and explicit boundary wrapping. Secret/PII scanner errors fail closed. Logs
store hashes, identifiers, counts, statuses, latency, and sanitized error codes;
private prompts or source are evidence artifacts, not routine log fields.

The blueprint's provider matrix is an example only. Phase 1 uses a default-deny
matrix, and live-provider testing requires human approval of each provider and
data class.

## Persistence and observability

- SQLite: runs, calls, transitions, reviews, validation failures, usage, and
  cost; all state transitions are auditable
- Evidence root: default `~/.model-council/runs/<project>/<run_id>/`
- Structured JSON logs: default `~/.model-council/logs/`, with no credentials
  or unnecessary source content
- Exports: raw council report and optional JSON snapshot generated from SQLite

## Testing strategy

- Layer 1: CLI smoke, Pydantic schema, transition policy, blind isolation,
  partial failure, idempotent call claim, and resume
- Layer 2: rubric-based fixture report checks and persistence/artifact
  reconciliation
- Layer 3: golden fixture prompts and acceptable structured responses; required
  before prompt or model-role changes
- Real-provider contract tests are opt-in and excluded from the default suite

## Migration slice

Phase 1 adds the application interface, three ports, fixture adapters, SQLite
adapter, local artifact adapter, minimal CLI, schemas, and tests. No external
provider dependency is required to pass verification.

## Residual risks

- Provider structured-output behavior may force adapter-specific repair logic.
- Exact model availability and pricing are unknown until credentials exist.
- Conservative artifact retention may capture proprietary source; retention and
  deletion policy must be approved before live use.
- SQLite is suitable for a local single-operator v0.x but not assumed adequate
  for multi-host concurrency.
