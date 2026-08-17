# Phase 1 Security and Operations Boundary

## Classification

Security/Ops review is required for Model Council because later phases will
handle provider credentials and potentially proprietary repository content.
Phase 1 deliberately has no network or provider adapter and needs no secret.

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

## Known residual risks

- Evidence artifacts may contain proprietary source supplied by the operator.
  Phase 1 has no automated retention/deletion policy.
- The SQLite adapter targets one local operator and is not safe for distributed
  multi-host execution.
- Fixture token counts are deterministic approximations, not provider billing
  truth.
- Secret/PII scanning and provider-specific data policy enforcement are Phase 2
  gates and must exist before any external egress is enabled.

## Phase 2 entry gate

Do not add a live provider adapter until the human governor approves provider
data classes, credentials, budget values, retention policy, and a low-risk test
corpus. Scanner or policy uncertainty must fail closed.
