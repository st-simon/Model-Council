# Phase 1 through Gate C Security and Operations Boundary

## Classification

Security/Ops review is required for Model Council because later phases will
handle provider credentials and potentially proprietary repository content.
Phase 1 deliberately has no network or provider adapter and needs no secret.
Phase 2A prepares the boundary offline. Phase 2B adds one Qwen adapter behind a
checked-in network deny policy. The first Beijing Gate C authorization made one
bounded probe, received terminal HTTP 403, and is now consumed and blocked.

## Enforced Phase 1 boundary

- Only the deterministic `FixtureModelGateway` is available.
- Reviewers receive bounded request objects and cannot access shell,
  filesystem, repository, connectors, or one another's output.
- Project, run, and reviewer identifiers reject path separators and traversal
  tokens before they can influence artifact paths.
- Project content is marked as untrusted evidence in each reviewer prompt.
- SQLite and the runtime artifact tree are local and ignored by Git.
- Operational JSONL logs contain identifiers, hashes, counts, model metadata,
  status, latency, and cost; they exclude prompts and source context.
- Raw prompts, context, and responses are evidence artifacts rather than log
  fields. Schema-repair attempts are retained separately and never overwritten.
- `.env`, local databases, logs, runtime outputs, caches, and virtual
  environments are ignored.

## Enforced Phase 2A boundary

- Checked-in provider configuration keeps `network_enabled: false`.
- `council verify-models` uses fixture capability declarations and performs no
  network call.
- Every configured review is packaged as a canonical `PromptEnvelope`; prompts,
  context, and section hashes are retained as evidence rather than routine logs.
- `GuardedModelGateway` applies secret, PII, injection, provider, and data-class
  checks before delegating. Missing policy, disabled network, or scanner failure
  denies egress.
- Credentials remain blank placeholders and are not inspected by Phase 2A.
- Logical calls and physical attempts are separately auditable. Retryable,
  terminal, invalid, and ambiguous timeout outcomes remain distinct.
- SQLite atomically reserves estimated cost before concurrent calls; hard-budget
  denial creates no provider attempt.

## Enforced Phase 2B model boundary

- The only provider adapter is Alibaba Cloud China Model Studio / Qwen through
  the workspace-specific Beijing (`cn-beijing`) HTTPS endpoint and direct HTTPX
  transport. Tokyo and generic DashScope endpoints are rejected.
- Business logic uses `architect_primary_v1`; the adapter resolves it to the
  approved `qwen3.7-max-2026-05-20` physical model.
- Capability declarations distinguish JSON mode, provider-enforced JSON Schema,
  and local schema validation. Beijing capability evidence records JSON Schema
  support, while the approved Gate C behavior remains JSON Object plus strict
  local validation.
- Provider-originated JSON output models use strict Pydantic validation and
  reject undeclared fields with `extra="forbid"`.
- Qwen responses must explicitly report `finish_reason="stop"`. Truncation,
  missing finish reason, or any other completion reason is terminal.
- Provider usage evidence must be non-negative; Qwen cached input tokens must
  not exceed reported prompt tokens. Invalid or internally inconsistent usage
  is a sanitized terminal invalid-response error and cannot reach cost or Gate C
  limit calculations.
- Provider errors are mapped to sanitized codes. Response bodies and credentials
  are excluded from routine logs.

## Consumed Gate C execution boundary

- Authorization `20260822-gate-c-qwen-beijing-live-verification` permits only the frozen
  synthetic `PUBLIC` corpus and hashes recorded in the authorization packet.
- Execution is isolated in `council gate-c-qwen`; the general review command
  remains fixture-backed and checked-in provider policy remains
  `network_enabled: false`.
- The command requires the exact approval ID, an explicit execute flag, all
  three console confirmations, confirmation that the offline suite passed, an
  open authorization window, a clean worktree, and an exact approved full commit
  SHA before it reads environment credentials.
- Credentials are accepted only from `DASHSCOPE_API_KEY` and
  `DASHSCOPE_WORKSPACE_ID`. They must belong to the Alibaba Cloud China
  (`aliyun.com`) Model Studio Beijing workspace; their values are not persisted
  or printed.
- The runner reserves the full RMB 0.20 ceiling before egress. It permits one
  256-token JSON probe followed conditionally by one 1,792-token review: at most
  two physical requests, one attempt each, no repair, and no retry.
- Thinking, tools, web search, streaming, inference logging, and prompt caching
  are disabled. Any observed cache use, physical-model drift, missing safe
  request ID, pricing drift, token/budget/time excess, or invalid strict output
  stops the run.
- The dedicated API key must be disabled, reset, or deleted immediately after
  evidence reconciliation. Local redacted evidence has a 30-day retention
  ceiling under Human Governor deletion ownership.

This authorization made one failed probe and cannot authorize another request.
No review call or retry occurred.

## Implemented temporary-key renewal boundary

The approved renewal removes the IP allowlist and replaces it with an exact-
model parent Key, a 900-second temporary Key, the existing RMB 0.20 runner hard
budget, and immediate parent-Key reset or deletion after reconciliation. The
temporary Key inherits all parent permissions and cannot be revoked before its
automatic expiry.

- The CLI reads the parent only from `DASHSCOPE_PARENT_API_KEY` after Git,
  corpus, policy, new-evidence-home, and Clash `127.0.0.1:7897` preflight.
- One fixed token request targets only
  `https://dashscope.aliyuncs.com/api/v1/tokens?expire_in_seconds=900`.
- The credential factory passes only the returned `st-*` temporary Key to the
  Beijing model adapter. Evidence records only its expiry and SHA-256
  fingerprint.
- A repository-local ignored authorization marker is created before token mint;
  it makes a mint failure, crash, probe failure, or completed run consume the
  authorization and prevents a second invocation.
- Failed HTTP responses retain only the internal error, an explicitly
  allowlisted Alibaba Cloud `code`, and a syntactically safe request ID in call,
  attempt, and JSONL evidence. Provider messages and bodies are discarded.
- A new run ID, `R-GATE-C-QWEN-BEIJING-002`, and a previously nonexistent home
  are mandatory. Gate C runtime homes are ignored by Git.
- The earlier proxy-failure evidence was proven to contain no provider/model,
  request ID, usage, cost, or output data, then atomically reconciled from
  `BLIND_REVIEW_RUNNING` to `FAILED` with
  `LOCAL_PROXY_PREFLIGHT_FAILED`. No provider request was made.

Alibaba Cloud does not provide a per-Key amount or token hard cap. The approved
RMB 1.00 provider cost threshold is advisory only. When available with
sufficient remaining quota, `free tier exhausted stop` is the provider-side
automatic spending stop. These controls are implemented and verified offline;
they do not authorize a provider request without later clean-SHA approval.

## Known residual risks

- Evidence artifacts may contain proprietary source supplied by the operator.
  Phase 1 has no automated retention/deletion policy.
- The SQLite adapter targets one local operator and is not safe for distributed
  multi-host execution.
- Fixture token counts are deterministic approximations, not provider billing
  truth.
- Regex scanners are a deterministic baseline, not a complete secret/PII
  classifier. Gate C therefore authorizes only the frozen synthetic public
  corpus, not repository source or internal data.
- Provider-side payload retention remains unknown. The provider states call data
  is not used for training, but that does not establish a precise deletion
  period.
- A timeout may have incurred cost even without a usable response; Gate C never
  retries that ambiguous outcome.
- Model identity, usage reporting, billing reconciliation, and JSON-mode
  reliability remain unverified after the terminal 403 probe.

## Gate C status

The Beijing authorization made one probe on 2026-08-23, received HTTP 403, and
stopped without a review or retry. Its Key must be revoked and its authorization
cannot be reused. The temporary-key renewal without an IP allowlist is
implemented and offline-verified, but renewed live execution remains
unauthorized until the Human Governor approves the clean implementation SHA and
confirms the execution prerequisites.
