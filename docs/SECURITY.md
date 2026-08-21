# Phase 1 and Phase 2A Security and Operations Boundary

## Classification

Security/Ops review is required for Model Council because later phases will
handle provider credentials and potentially proprietary repository content.
Phase 1 deliberately has no network or provider adapter and needs no secret.
Phase 2A prepares the boundary offline and preserves that restriction.

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

## Known residual risks

- Evidence artifacts may contain proprietary source supplied by the operator.
  Phase 1 has no automated retention/deletion policy.
- The SQLite adapter targets one local operator and is not safe for distributed
  multi-host execution.
- Fixture token counts are deterministic approximations, not provider billing
  truth.
- Regex scanners are a deterministic baseline, not a complete secret/PII
  classifier. Gate B security review must approve or strengthen scanners for the
  selected provider and test corpus.
- Phase 2A does not verify provider retention, training use, endpoint region,
  pricing, or real model identity.

## Phase 2B/C entry gates

Do not add a live provider adapter until the human governor approves provider
data classes, credentials, budget values, retention policy, and a low-risk test
corpus. Gate B must also approve the exact dependency/transport. Gate C must
record the frozen corpus hash, exact egress material, call/token/attempt ceilings,
and stop conditions. Scanner or policy uncertainty must fail closed.
