# Model Council Phase 2 — Provider Verification and Guarded Live Review

- Proposal ID: `20260821-phase-2-provider-verification`
- Status: `implemented`
- Date: 2026-08-21
- Gate A approved: 2026-08-21 by Human Governor
- Gate B approved: 2026-08-21 by Human Governor
- Gate C approved: 2026-08-21 by Human Governor
- Gate C Beijing replacement approved: 2026-08-22 by Human Governor
- Owner: Codex (Coordinator / Architect / Builder after approval)
- Human governor: user
- Depends on: verified Phase 1 proposal `20260818-model-council-mvp0`

## Background

Phase 1 proved an offline, fixture-backed vertical slice: four isolated reviewer
roles can run concurrently, persist results in SQLite, tolerate partial failure,
resume without duplicating a logical call, and export auditable evidence. It did
not authorize provider credentials, network calls, model slugs, or repository
content leaving the machine.

Phase 2 introduces the first real-provider boundary. This changes the project's
security, privacy, cost, reliability, and recovery profile. Provider behavior is
variable; pricing and capabilities can change; source context may be proprietary;
and a failed request may have been billed even when no response was received.
The transition therefore needs an explicit data boundary, attempt-level recovery,
capability verification, and two distinct human approvals: implementation
approval and live-test authorization.

An external Gemini design review dated 2026-08-21 was considered as advisory
input. Its strongest Phase 2 contributions are retry-aware reviewer state,
capability-gated prompt caching, structured challenger output, and static/dynamic
prompt separation. Its governance, finding deduplication, adaptive routing,
audit-fix, and full Graph-RAG recommendations remain assigned to Phase 3 or 4.

## Purpose

Connect one approved provider at a time without weakening blind-review isolation,
the default-deny data policy, SQLite's authority, logical model aliases, or the
human governor's control over data, credentials, and budget.

The first reliable Phase 2 workflow is:

1. validate a provider and logical model alias against declared capabilities;
2. inspect and authorize a bounded, low-risk prompt envelope for egress;
3. make one retry-safe structured review call within a hard budget;
4. persist each attempt, usage record, sanitized failure, and immutable evidence;
5. resume without repeating successful work or blindly retrying terminal errors.

## Scope

### Phase 2A — Offline provider-readiness slice

- Split role, logical-model, provider, prompt, and policy configuration.
- Add a versioned `PromptEnvelope` with static and dynamic sections and hashes.
- Add deterministic egress scanning and a default-deny provider/data policy.
- Add provider capability declarations and fixture-backed capability probes.
- Separate logical calls from physical call attempts in SQLite.
- Add retry classification, bounded backoff metadata, timeout states, and resume.
- Extend usage accounting for cached and uncached input tokens.
- Add soft and hard run-budget policies.
- Require structured challenger fields: evidence, minimal alternative, trade-off,
  and residual risk.
- Add migrations, fixture contract tests, failure tests, and documentation.

Phase 2A performs no network request and requires no credential.

### Phase 2B — One-provider adapter slice

- Add exactly one approved provider adapter behind `ModelGateway`.
- Select the provider SDK or HTTP client only after dependency and security review.
- Map provider-specific errors into stable transient, throttled, timeout,
  invalid-response, policy, authentication, and terminal categories.
- Implement `council verify-models` for the approved provider and alias.
- Capture actual model identity, declared/observed capabilities, latency, token
  usage, cache usage, request ID when safe, and pricing snapshot provenance.
- Run adapter contract tests against mocks or a local fake endpoint by default.

Phase 2B may be implemented only after the provider/data row and credential
mechanism have been approved. It does not itself authorize a live request.

### Phase 2C — Guarded low-risk live verification

- Run one minimal capability verification against the approved provider.
- Run one bounded review against the approved frozen, low-risk corpus.
- Reconcile provider-reported usage, local budget accounting, SQLite state,
  evidence artifacts, and sanitized logs.
- Record whether prompt caching is supported and whether it produced a measured
  benefit; no savings target is assumed in advance.
- Stop after the approved calls and publish a verification record for human review.

Phase 2C requires a separate live-test authorization containing the exact
provider, data class, model alias, credential source, call ceiling, budget, and
test-corpus commit or content hash.

## Non-goals

- No semantic finding deduplication, embeddings, normalization, debate, appeal,
  Codex decision, P0/P1 escalation, or audit-fix loop; these remain Phase 3.
- No full repository Context Builder, Tree-sitter dependency graph, Graph-RAG,
  baseline experiment, adaptive membership, or final-audit routing; these remain
  Phase 4.
- No provider fallback across trust boundaries. Cross-provider fallback remains
  disabled until both provider/data policies are independently approved.
- No hosted service, multi-user operation, Redis, PostgreSQL, queue, containers,
  MCP, GitHub App, or deployment.
- No reviewer shell, filesystem, repository-browse, connector, or write access.
- No automatic commits, pushes, PR updates, or target-repository mutation.
- No hard-coded provider model slug in application or governance logic.
- No mandatory prompt caching and no unverified 50%–70% savings claim.

## Proposed approach

### 1. Preserve the orchestration core and deepen its seams

Keep `CouncilApplication`, `ModelGateway`, `RunStore`, and `ArtifactStore` as the
main application boundary. Add one deterministic `EgressGuard` domain service at
the point immediately before `ModelGateway` receives an approved payload. The
guard owns scanning and policy evaluation; the provider adapter never decides
whether source content is allowed to leave the machine.

Do not add a separate cache port. Prompt caching is provider behavior exposed
through capabilities and usage records. This keeps provider-specific cache keys,
TTL, minimum-prefix rules, and billing inside the adapter while keeping prompt
structure and audit hashes provider-neutral.

### 2. Introduce a provider-neutral prompt envelope

`PromptEnvelope` contains versioned sections:

- `static_prefix`: system constraints, role instructions, output schema;
- `project_context`: explicitly approved project constraints and bounded context;
- `dynamic_payload`: task, proposal, and approved change material;
- `policy_metadata`: data class, provider policy version, prompt version;
- independent hashes for each section and the canonical full envelope.

Static-prefix ordering enables provider caching where supported. Phase 2 only
assembles deterministic bounded inputs; dependency-graph retrieval is deferred.

### 3. Model logical calls and physical attempts separately

Retain the existing unique logical-call identity. Add a child `call_attempts`
record for each physical provider request. The intended attempt lifecycle is:

```text
PENDING -> RUNNING -> SUCCEEDED
                   -> RETRY_WAIT -> RUNNING
                   -> TIMED_OUT
                   -> INVALID
                   -> FAILED_TERMINAL
```

Each attempt records an ordinal, start/end time, error class, sanitized error
code, retry eligibility, `next_retry_at`, provider/model identity, usage, latency,
cache counters, and cost. Successful logical calls remain reusable. Authentication,
policy, invalid-request, and hard-budget failures are terminal. Network,
rate-limit, and selected timeout failures are retryable only within the approved
attempt and budget limits.

The store performs atomic attempt acquisition and completion. The application
asks the store for the next eligible action instead of reconstructing retry
semantics from row status. A lease or heartbeat is added only if real execution
shows concurrent-process recovery needs it; Phase 2 remains single-host.

### 4. Probe capabilities before workload calls

`ProviderCapabilities` is keyed by logical alias and records:

- resolved provider and actual model identity;
- structured-output and schema limitations;
- supported context/output limits;
- timeout and rate-limit behavior available to the adapter;
- prompt-cache support, minimum prefix, TTL modes, and usage fields;
- usage and price metadata availability;
- provider region or endpoint class relevant to the approved data policy.

Capabilities are observed evidence, not permanent truth. Verification records
include timestamps and configuration hashes. A mismatch between required and
observed capability blocks the review call.

### 5. Fail closed at the egress boundary

Before any live call, the egress guard evaluates the complete canonical envelope:

- secret scan;
- PII/data-class classification;
- prompt-injection heuristics for untrusted repository content;
- provider/data matrix lookup;
- maximum context and artifact-size limits;
- approved provider, alias, endpoint class, and policy version.

Scanner errors, missing policy rows, unresolved classification, capability
mismatch, or configuration drift deny egress. Credentials are never included in
the envelope, evidence artifacts, SQLite payload columns, or operational logs.

### 6. Make budgets authoritative before calls

The application evaluates budget before every new physical attempt. Policy
includes a per-call output ceiling, per-run soft limit, per-run hard limit,
maximum attempts, and an approved currency/pricing snapshot. The soft limit
allows already-running work to finish but starts no optional call. The hard limit
starts no new call and preserves a resumable partial run. Unknown pricing cannot
be treated as zero; it requires an explicit bounded fallback estimate or blocks
the live call.

Recorded usage distinguishes:

- uncached input tokens;
- cache-creation input tokens;
- cache-read input tokens;
- output tokens;
- estimated pre-call cost;
- provider-reported or locally calculated post-call cost;
- pricing source, timestamp, and currency conversion source when applicable.

### 7. Keep challenger structure separate from routing policy

The challenger role's Phase 2 output schema requires `evidence`,
`minimal_alternative`, `trade_off`, and `residual_risk` for each radical
challenge. This is an output-quality contract, not authorization to dynamically
skip or add reviewers. Controlled Phase 2 tests continue to exercise all approved
roles. Adaptive Grok routing waits for Phase 4 evidence on noise, marginal
detection value, latency, and cost.

## Alternatives considered

### Unified gateway library first

Deferred. A unified library may accelerate support for several providers, but it
adds another trust, error-mapping, caching, and credential layer before this
project has validated one live adapter. Reconsider after two direct adapters show
meaningful duplicated behavior.

### Provider logic inside `CouncilApplication`

Rejected. It would leak SDK types, retry rules, caching, and usage quirks into the
orchestration core and make fixture/live contract equivalence harder to verify.

### Egress checks inside each provider adapter

Rejected. Provider adapters should not authorize their own data access. A single
pre-gateway guard provides one fail-closed policy path and focused tests.

### Full Saga or external workflow engine

Deferred. The system needs attempt records and retry transitions, not distributed
compensation. SQLite and a single-host application remain sufficient until real
concurrency or recovery evidence proves otherwise.

### Mandatory provider prompt caching

Rejected. Cache support, thresholds, TTL, write premiums, and usage reporting
vary. Phase 2 structures prompts for cacheability, probes support, and measures
actual results without making cache availability a correctness dependency.

### Tree-sitter / Graph-RAG in Phase 2

Deferred to Phase 4. A deterministic bounded manifest is sufficient to verify the
provider boundary. Adding parsing and retrieval now would mix context-quality
experiments with security, billing, and recovery verification.

## Implementation steps

Each step is a separate observable vertical slice. Do not advance while its
focused tests fail.

1. **Configuration and prompt contract**
   - Split logical aliases, role assignments, prompt versions, and provider
     declarations.
   - Add canonical `PromptEnvelope` construction and hash tests.
   - Keep fixture behavior passing through the same envelope.
2. **Attempt persistence and recovery**
   - Add a reversible SQLite migration for `call_attempts` and required call
     metadata.
   - Add retry classification and atomic attempt transitions.
   - Verify resume reuses successes, retries only eligible failures, and stops at
     attempt or budget limits.
3. **Egress guard**
   - Add deterministic scanners and provider/data policy evaluation.
   - Verify deny-by-default, scanner failure, credential-pattern detection,
     unresolved PII, injection-marker handling, and sanitized denials.
4. **Capability verification**
   - Add provider-neutral capabilities and `council verify-models`.
   - Exercise it through fixtures/fakes with capability mismatch tests.
5. **Usage, caching, and budget accounting**
   - Add pre-call estimates and post-call usage reconciliation.
   - Record cache counters when available and preserve `unknown` distinctly from
     zero.
6. **First provider adapter**
   - Begin only after Phase 2B gates are satisfied.
   - Select one provider and the smallest reviewed dependency.
   - Pass the same adapter contract suite used by the fixture/fake.
7. **Guarded live verification**
   - Begin only after the Phase 2C live-test authorization is recorded.
   - Run the approved capability probe and one bounded low-risk review.
   - Reconcile state, evidence, usage, cost, logs, and provider dashboard data
     where available.
8. **Closeout and decision**
   - Record verification results and residual risks.
   - Do not add a second provider until the first adapter and live run pass.

## Ownership and affected paths

- Proposal and project state:
  - `proposals/active/20260821-phase-2-provider-verification.md`
  - `TASKS.md`, `DECISIONS.md`, relevant `docs/`
- Domain and application contracts:
  - `src/model_council/models.py`
  - `src/model_council/ports.py`
  - `src/model_council/application.py`
- Adapters and migrations:
  - `src/model_council/adapters/`
  - `migrations/`
- Configuration and prompts:
  - `config/`
  - `prompts/`
  - `.env.example` placeholders only
- Tests and approved fixtures:
  - `tests/`
  - `tests/fixtures/`
- Runtime evidence and credentials:
  - ignored local runtime paths only; never committed
- Reviewed target repository:
  - read-only evidence source; no write authority is granted by this proposal

Codex owns project file changes after the applicable approval. The human governor
owns provider/data policy, credential provisioning, budget, and live-test
authorization.

## Security/Ops classification

**Required.** Phase 2 introduces external APIs, credentials, source-content
egress, provider retention considerations, mutable pricing/capabilities, network
failure, rate limits, and potentially billed retries.

Security/Ops must review the exact provider before Phase 2B and re-check the
approved live-test envelope before Phase 2C. Required evidence includes the
provider/data matrix, credential mechanism, endpoint/region, retention or
training setting where applicable, scanner results, budget, retry limits, and
test-corpus hash.

## Approval gates

### Gate A — Proposal approval

Approves the architecture, phased scope, planned project paths, and Phase 2A
offline implementation. It does not approve a dependency download, provider
credential, network call, or source-code egress.

### Gate B — Provider adapter approval

Required before Phase 2B. The human governor approves:

- provider and endpoint/region;
- allowed and denied data classes;
- retention/training policy assumptions;
- credential source and rotation/revocation expectations;
- exact dependency or transport choice;
- candidate logical alias and required capabilities.

### Gate C — Live-test authorization

Required before Phase 2C. The human governor approves:

- frozen test repository/commit or corpus hash;
- exact material permitted to leave the machine;
- provider, alias, endpoint, and policy version;
- maximum calls, attempts, tokens, and total spend;
- test window and stop conditions.

Any Gate B or C field left unknown is a blocker, not an implied default.

## Risks and mitigations

- **Proprietary or secret content leaves the machine** — default deny; scan the
  complete canonical envelope; fail closed on uncertainty; use only an approved
  low-risk corpus for the first run.
- **Prompt injection alters reviewer behavior** — mark repository content as
  untrusted evidence, delimit it structurally, scan for suspicious instructions,
  and give it no tool or write access.
- **Retry creates duplicate billing** — persist physical attempts and provider
  request IDs where safe; retry only classified transient failures within hard
  limits; never retry authentication, policy, or invalid-request errors.
- **Timeout outcome is ambiguous** — record `TIMED_OUT` separately; do not claim
  the call was unbilled; require explicit retry eligibility.
- **Provider capability or model identity drifts** — timestamp probes, compare
  required/observed capabilities, and block mismatches.
- **Cache accounting is misleading** — record cache creation/read tokens
  separately; use measured provider fields; preserve unknown values.
- **Price changes invalidate estimates** — version pricing snapshots and record
  estimate versus actual; unknown pricing blocks or uses an explicitly approved
  conservative ceiling.
- **SQLite migration damages recoverability** — use an Alembic migration, back up
  the test database, verify upgrade on a Phase 1 fixture database, and document
  recovery; no distributed execution.
- **Adapter abstraction mirrors one provider** — keep project-domain requests,
  errors, capabilities, and usage models; verify with fixture and fake adapters.
- **Phase 3/4 scope leaks into provider work** — use the explicit non-goals and
  external-review disposition below as review gates.

## Validation plan

### Default offline suite

- Existing Phase 1 tests continue to pass without credentials or network.
- Prompt-envelope canonicalization and section hashes are deterministic.
- Reviewer isolation remains intact with the new envelope.
- Egress is denied for missing policy, scanner error, secret match, disallowed
  data class, alias mismatch, and capability mismatch.
- Attempt transitions reject illegal or stale completions.
- Resume skips successful calls, retries only eligible attempts, and respects
  attempt/time/budget ceilings.
- Provider errors are sanitized and mapped to stable categories.
- Unknown cache/price/usage fields remain unknown rather than becoming zero.
- Fixture and fake provider adapters pass the same public contract tests.

### Migration and reconciliation

- Upgrade a copy of a Phase 1 SQLite database and preserve existing run/call
  history.
- Reconcile logical calls, attempts, reviews, evidence hashes, logs, usage, and
  reports after success, timeout, retry, invalid output, and hard-budget stop.

### Opt-in live verification

- Excluded from the default test suite and impossible without Gate C inputs.
- Verify actual model identity and required capabilities.
- Run only the approved bounded corpus and call ceiling.
- Compare local usage/cost with provider-reported evidence where available.
- Inspect artifacts and logs for credential or unnecessary source leakage.

### Required local commands

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
git diff --check
```

Provider-specific offline verification uses:

```bash
uv run pytest -q tests/test_phase2b_qwen_adapter.py
uv run council verify-models --config-dir config
```

## Done criteria

Phase 2 is `verified` only when:

1. Phase 1 remains green and credential-free by default.
2. The approved provider passes capability and adapter contract verification.
3. The egress guard demonstrably fails closed for all listed denial paths.
4. Call attempts, retry eligibility, timeout ambiguity, and resume are auditable.
5. Soft/hard budgets prevent unapproved new calls and preserve partial state.
6. One Gate-C-approved low-risk live review completes or produces a correctly
   governed partial/failure result.
7. SQLite, artifacts, logs, usage, and provider evidence reconcile.
8. No credential, prohibited source content, or unsanitized provider error is
   committed or written to routine logs.
9. Security/Ops has no unresolved P0/P1 finding.
10. Residual provider, retention, pricing, and recovery risks are documented.

## State transition plan

- Current: `implemented` — Beijing Gate C replacement approved and guarded
  execution implemented offline; live verification has not started
- Gate A approval recorded on 2026-08-21
- Gate B approval recorded on 2026-08-21
- When Phase 2A implementation starts: `in_progress`
- If Gate B inputs are missing after Phase 2A: remain `in_progress` with the
  provider slice explicitly blocked; do not mislabel Phase 2 as complete
- After Phase 2A/2B code is complete: `implemented`
- After Gate C live verification and all done criteria pass: `verified`
- Move to `archive/` only when Phase 2 has no open acceptance gap
- Use `blocked` when a required approval, provider capability, credential,
  budget, policy, or test corpus prevents safe progress
- Use `superseded` if a later approved proposal replaces this design

## Phase 2A verification record

Verified offline on 2026-08-21:

- role/model/provider configuration and versioned prompt templates;
- canonical section-hashed `PromptEnvelope` used by fixture reviews;
- strict challenger falsification schema;
- logical-call and physical review/repair attempt persistence;
- retry-aware resume with preserved timeout ambiguity;
- fail-closed guarded gateway for policy, secret, PII, injection, and scanner
  failure cases;
- offline `council verify-models` for all configured fixture aliases;
- separate cache creation/read/uncached usage fields;
- atomic budget reservations across concurrent reviewers;
- Phase 1 regression, migration, CLI, security-boundary, recovery, usage, and
  budget tests.

At the Phase 2A closeout, no dependency was installed, no credential was read,
and no network or provider call was made. Phase 2B was not yet authorized at
that checkpoint; its later approval and implementation are recorded below.

## Gate B decision and Phase 2B verification record

Gate B was approved by the Human Governor on 2026-08-21 with this exact row:

- provider: Alibaba Cloud Model Studio / Qwen;
- endpoint: Tokyo workspace-specific OpenAI-compatible endpoint;
- data class: `PUBLIC` only; all non-public, PII, secret, and credential data denied;
- logical alias: `architect_primary_v1`;
- pinned model: `qwen3.7-max-2026-05-20`;
- transport: `httpx>=0.28.1,<0.29`, direct Chat Completions HTTP;
- credential source: `DASHSCOPE_API_KEY`, with workspace ID supplied separately;
- provider call data is assumed not used for training per provider documentation;
  payload retention remains unknown;
- provider inference logging and prompt caching remain disabled.

Phase 2B was implemented and verified offline on 2026-08-21. The adapter maps
sanitized authentication, throttling, timeout, transport, invalid-request, and
invalid-response errors; captures model identity, usage/cache fields, latency,
safe request ID, and pricing snapshot provenance; and passes mock-transport
contract tests. `council verify-models` verifies the approved alias without
credentials or a provider call. Checked-in policy remains `network_enabled:
false`; no credential was read and no external model request was made.

The proposal is `implemented` but not `verified`; Gate C live evidence remains
pending.

### Beijing replacement record

On 2026-08-22 the Human Governor superseded the unused Tokyo provider boundary
with Alibaba Cloud China Model Studio Beijing (`cn-beijing`) while preserving
the model, synthetic public workload, call and token ceilings, zero retries,
RMB 0.20 hard budget, execution window, and retention rules. The replacement
authorization is
`proposals/active/20260822-gate-c-qwen-beijing-live-verification.md`. The Tokyo
packet remains an audit record and cannot authorize a request.

## Gate C preparation record

An independent Gate C authorization packet was prepared on 2026-08-21 at
`proposals/active/20260821-gate-c-qwen-live-verification.md`. It freezes a
synthetic PUBLIC corpus and exact envelope hashes, limits the run to one JSON
capability probe followed conditionally by one review, forbids retries, and sets
explicit token, spend, time, stop, credential, and retention boundaries. Its
Tokyo status is now `superseded`; the Beijing replacement is `approved`. The
Human Governor also approved capability-field
splitting, strict provider-output models with `extra="forbid"`, and terminal
`finish_reason` checks as implementation prerequisites. The guarded runner and
offline tests are implemented; no credential has been read and no live provider
request has been made. Execution remains conditional on a clean approved commit,
the 2026-08-22 through 2026-08-28 JST window, and all console/credential
preconditions.

## External-review disposition

| Advisory suggestion | Disposition | Phase |
|---|---|---|
| Reviewer substate and idempotent resume | Modified: logical calls plus physical attempts; no Saga framework | 2 |
| Prompt caching | Modified: capability-gated and measured, never mandatory | 2 |
| Static/dynamic prompt structure | Accepted as `PromptEnvelope` | 2 |
| Challenger falsification fields | Accepted as structured output contract | 2 |
| Immutable P0/P1 severity and escalation | Accepted in principle, deferred to finding governance | 3 |
| Conservative multi-anchor dedup | Modified; ambiguous items stay separate | 3 |
| Audit-fix introduced-defect classification | Accepted in principle | 3 |
| Dynamic challenger routing | Deferred until baseline evidence exists | 4 |
| Tree-sitter / Graph-RAG | Deferred behind context-quality benchmarks | 4 |
| Phase 01-A/B/C renumbering | Rejected; retain the approved phase model | — |
| Fixed semantic threshold or 50%–70% savings target | Rejected without workload evidence | — |

## Gate C remaining execution conditions

- Execute only from a clean, explicitly approved full commit SHA.
- Confirm the dedicated key scope, disabled inference logging, and billing
  access before the command reads credentials.
- Execute only inside the approved window and revoke or delete the key after
  reconciliation.

## References

- `MODEL_COUNCIL_PHASE01_OPTIMIZATION_SUGGESTIONS.md`, Gemini external design
  review, 2026-08-21. Advisory input only; dispositions are recorded above.
- Anthropic, [Pricing and prompt caching](https://docs.anthropic.com/en/docs/about-claude/pricing):
  provider caching has distinct write/read pricing and must be measured rather
  than assumed.
- Alibaba Cloud Model Studio,
  [Context cache](https://help.aliyun.com/en/model-studio/context-cache): cache
  behavior and usage fields are provider/model dependent.
- Liu et al., [Lost in the Middle](https://arxiv.org/abs/2307.03172): long-context
  performance depends on information placement; this supports later context
  experiments but does not by itself justify Graph-RAG in Phase 2.

## Approval request

**Gate A and Gate B were approved on 2026-08-21; the Gate C Beijing replacement
was approved on 2026-08-22.** Phase 2A, the offline Phase 2B Qwen adapter, and
the guarded Gate C runner are implemented. Gate C live execution is authorized
only under the Beijing packet's exact
corpus, commit, endpoint, limits, budget, time window, console confirmations,
and stop conditions. No live request has yet been made.
