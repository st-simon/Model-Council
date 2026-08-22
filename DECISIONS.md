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

- Status: superseded on 2026-08-22 by D-010; retained as the Gate B audit record
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

## D-010 — Replace the unused Tokyo boundary with Beijing

- Status: accepted by the Human Governor on 2026-08-22
- Decision: retain the direct HTTPX adapter, alias
  `architect_primary_v1`, pinned model `qwen3.7-max-2026-05-20`, synthetic
  `PUBLIC` corpus, two-request/no-retry limit, and RMB 0.20 hard budget; replace
  only the provider location with Alibaba Cloud China (`aliyun.com`) Model
  Studio Beijing, region `cn-beijing`.
- Endpoint boundary: accept only workspace hosts ending in
  `.cn-beijing.maas.aliyuncs.com` with the approved compatible-mode path. Reject
  Tokyo, international, generic DashScope, query-bearing, and alternate hosts.
- Credential boundary: use only a dedicated Beijing workspace key and ID through
  the existing environment-variable inputs. No credential may be read before
  the guarded live preflight passes.
- Capability boundary: declare Beijing JSON Schema support separately, while
  keeping Gate C request behavior at JSON Object plus strict local Pydantic
  validation.
- Reason: the available account must use the China-site Beijing service; a
  single-region allowlist minimizes accidental cross-region egress.

## D-011 — Proposed temporary-key replacement for IP allowlisting

- Status: accepted and implemented offline on 2026-08-23; renewed live
  execution still requires clean-SHA approval
- Decision requested: remove the API Key IP allowlist and instead mint a
  900-second temporary Key from an exact-model Beijing parent Key. Keep the
  frozen `PUBLIC` corpus, two-inference-request ceiling, zero retry, and RMB 0.20
  runner hard budget.
- Provider limitation: temporary Keys cannot be manually deleted before expiry
  and inherit all parent-Key permissions. Alibaba Cloud cost thresholds notify
  but do not impose a per-Key hard stop.
- Additional controls: keep the parent Key out of the model adapter, reset or
  delete it immediately after reconciliation, use free-tier exhausted stop when
  available, and retain only allowlisted provider error codes and safe request
  IDs.
- Gate boundary: implementation and offline verification are authorized. A
  renewed provider request is not authorized until the Human Governor approves
  the clean implementation SHA.
- Implementation record: the parent-to-temporary credential factory, fixed
  900-second token endpoint, one-shot authorization marker, sanitized provider
  error evidence, new run/home boundary, proxy preflight, and legacy local
  failure reconciliation are complete and covered by offline tests.
