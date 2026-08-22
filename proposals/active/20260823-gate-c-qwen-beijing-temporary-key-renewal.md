# Gate C Renewal — Qwen Beijing Temporary-Key Live Verification

- Proposal ID: `20260823-gate-c-qwen-beijing-temporary-key-renewal`
- Proposed authorization ID: `20260823-gate-c-qwen-beijing-temporary-key-renewal`
- Status: `in_progress` — offline implementation complete; clean commit pending;
  no live request authorized
- Date prepared: 2026-08-23
- Date approved: 2026-08-23 by Human Governor
- Parent proposal: `20260821-phase-2-provider-verification`
- Prior consumed authorization: `20260822-gate-c-qwen-beijing-live-verification`
- Decision owner: Human Governor
- Executor after approval and clean-commit approval: Codex

## Decision requested

Approve a replacement Gate C boundary that removes the API Key IP allowlist and
uses a 900-second Alibaba Cloud temporary API Key, exact model scope, the
existing RMB 0.20 runner hard budget, and immediate parent-key revocation after
reconciliation. A provider cost alert is retained as advisory detection, not as
a hard spending control.

Approval of this proposal would authorize implementation and offline
verification first. It would not authorize a live request until the Human
Governor separately names the clean implementation commit SHA and confirms all
execution prerequisites.

## Prior attempt and reason for renewal

The prior authorization made one JSON probe through the Beijing endpoint on
2026-08-23 at 00:23 JST and received HTTP 403. No review request or retry was
made. Retained evidence contains no usage, cost, safe request ID, or Alibaba
Cloud error code beyond the HTTP status.

The local shell routes proxy-aware CLI traffic through Clash Verge at
`127.0.0.1:7897`. An IP allowlist tied to a VPN exit creates an unstable coupling
between credential validity and proxy-node routing. The replacement removes
that coupling and narrows the credential's lifetime and model permissions
instead.

## Unchanged model and data boundary

| Field | Proposed value |
|---|---|
| Provider | Alibaba Cloud China Model Studio |
| Region | China (Beijing), `cn-beijing` |
| Model endpoint | `https://{DASHSCOPE_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions` |
| Logical alias | `architect_primary_v1` |
| Physical model | `qwen3.7-max-2026-05-20` |
| Data class | Frozen synthetic `PUBLIC` corpus only |
| Inference requests | One probe, then one conditional review |
| Retry and repair | None |
| Inference logs | Not authorized / disabled |
| Tools, web, cache, streaming | Disabled |
| Internal hard budget | RMB 0.20 |

The frozen corpus and hashes remain those recorded in the consumed Beijing
authorization. Repository source, internal data, credentials, prior responses,
and additional context remain prohibited.

## Replacement credential boundary

1. Create a new permanent parent Key in the approved Beijing workspace. Its
   custom permissions must allow only `qwen3.7-max-2026-05-20`. No IP allowlist
   is required.
2. Supply the parent Key only as `DASHSCOPE_PARENT_API_KEY` to the controlled
   token-mint step. Do not pass it to `QwenModelGateway`, persist it, or print it.
3. After all offline and Git preflight checks pass, make one authorized control-
   plane request to
   `https://dashscope.aliyuncs.com/api/v1/tokens?expire_in_seconds=900`.
4. Hold the returned temporary Key only in process memory and use it as the
   bearer credential for the Gate C model requests. Record only its expiry
   timestamp and a non-reversible fingerprint.
5. The temporary Key automatically expires after 900 seconds. Alibaba Cloud
   does not support manually deleting a temporary Key before expiry.
6. Reset or delete the parent Key immediately after evidence reconciliation or
   on any uncertainty. Never commit, chat, log, or persist either Key.

The temporary Key inherits all permissions of the parent Key. Exact parent
model scope is therefore mandatory and replaces the removed network-location
control.

## Request, token, time, and cost ceilings

| Limit | Proposed ceiling |
|---|---:|
| Credential control-plane requests | 1 |
| Model inference requests | 2 maximum |
| Model attempts | 1 per operation |
| Probe output | 256 tokens |
| Review output | 1,792 tokens |
| Aggregate input | 3,000 tokens |
| Aggregate output | 2,048 tokens |
| Runner wall clock | 10 minutes |
| Temporary-Key TTL | 900 seconds |
| Runner hard budget | RMB 0.20 |
| Advisory provider cost alert | RMB 1.00 |

Alibaba Cloud currently does not support a per-API-Key daily or monthly token
or amount limit that automatically stops model calls. Its budget and cost
thresholds send delayed notifications and do not limit resource use. The RMB
1.00 provider alert is therefore detection only; it is not a substitute for the
runner hard budget, temporary credential, model scope, or prompt limits.

If the exact model still has sufficient newcomer free quota, execution must
enable `free tier exhausted stop` and confirm more than 5,048 tokens remain.
That feature is the only available provider-side automatic spending stop in
this scenario. If the model or account cannot enable it, renewed live execution
requires that limitation to be disclosed at final approval.

## Proxy and endpoint boundary

- Business policy continues to route CLI traffic through Clash Verge.
- Preflight must confirm the local proxy listener is reachable at
  `127.0.0.1:7897` and the shell proxy variables select it.
- No proxy exit IP is trusted as an authentication factor or written to the
  repository.
- The model adapter continues to reject Tokyo, international, trial, generic
  DashScope model endpoints, query strings, and alternate paths.
- The generic Beijing DashScope endpoint is authorized only for the single
  temporary-token mint request.

## Diagnostic and evidence prerequisites

Before another live request, implementation must:

1. retain only an allowlisted Alibaba Cloud error `code` and syntactically safe
   `request_id` for failed HTTP responses; never retain the provider message or
   response body;
2. use a new run ID and evidence home rather than resume either failed run;
3. ignore `.model-council-gate-c/` in Git while retaining its evidence under the
   existing 30-day local retention rule;
4. reconcile the earlier proxy-failure database from `RUNNING` to an explicitly
   documented local pre-provider failure without issuing a request;
5. verify the exact workspace/model permission and confirm the failed Key has
   been revoked or reset;
6. pass the full offline suite from a clean implementation commit.

## Security implications

Removing the IP allowlist means possession of the parent or temporary Key is
sufficient to call the permitted model from any network during that Key's
lifetime. The main residual risks are unauthorized spend, quota exhaustion, and
provider-account abuse. The replacement controls reduce duration and scope but
do not make credential theft harmless.

The permanent parent Key is the highest-risk credential because the temporary
Key inherits its permissions. It must exist only for the bounded mint-and-run
workflow and be reset or deleted immediately afterward. The temporary Key's
900-second fixed lifetime cannot be shortened after issuance.

## Alternatives considered

- Dedicated static VPN egress plus IP allowlist: strongest network control, but
  not selected because exclusive, provider-guaranteed static egress has not been
  established for the required proxy route.
- Shared VPN-node IP allowlist: rejected because the exit may change and is not
  exclusive to this operator.
- Long-lived Key without IP allowlist: rejected because model scope alone does
  not bound exposure duration.
- Provider budget threshold as hard control: rejected because Alibaba Cloud
  documents it as notification only.
- Free-tier stop as the only control: rejected because availability and
  remaining quota can change; it is additive when available.

## Implementation scope

- Add a temporary-token mint seam that keeps the parent Key out of the model
  adapter.
- Add strict expiry and credential-fingerprint evidence without secret values.
- Preserve sanitized provider error code and safe request ID on HTTP failures.
- Add a new authorization ID, run ID, and evidence-home boundary.
- Ignore Gate C runtime evidence in Git and add reconciliation tests for failed
  pre-provider and terminal-provider attempts.
- Synchronize README, Security/Ops, decisions, and task status.

## Validation plan

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
git diff --check
```

Focused tests must prove that the parent Key never reaches the adapter, the
temporary Key expires within policy, no secret is persisted, error evidence is
allowlisted, failed runs cannot resume, Git ignores runtime evidence, and the
token-mint/model request ceilings fail closed.

## Proposed execution window and stop conditions

- Window: 2026-08-24 09:00 through 2026-08-28 21:00 JST.
- Any token-mint failure consumes the control-plane allowance and stops.
- Any probe failure consumes the first inference allowance and stops.
- Any ambiguous timeout stops without retry.
- Missing free-tier-stop evidence, when the feature is available, stops.
- Parent-Key revocation uncertainty stops final reconciliation.

## State transition plan

- Current: `in_progress` — offline implementation and verification complete;
  clean commit pending; no request authorized.
- After a green clean commit: `implemented`, live execution still pending SHA
  approval.
- After explicit full-SHA approval: one renewed run may start in the window.
- After reconciliation, temporary-Key expiry, and parent-Key revocation:
  `verified` or `blocked`.

## Authoritative sources

- https://help.aliyun.com/zh/model-studio/generate-temporary-api-key
- https://help.aliyun.com/zh/model-studio/get-api-key
- https://help.aliyun.com/zh/model-studio/model-telemetry
- https://help.aliyun.com/zh/user-center/how-to-manage-a-budget
- https://help.aliyun.com/zh/model-studio/new-free-quota

## Approval record

The Human Governor approved this proposal on 2026-08-23 and requested
implementation. Approval accepts that the RMB 1.00 provider threshold is
advisory, not a hard spending cap, and that a 900-second temporary Key cannot be
revoked before its automatic expiry. Live execution remains separately gated by
the clean implementation commit SHA.

## Implementation record

Offline implementation completed on 2026-08-23 without reading a credential or
making a provider request. The implementation adds the fixed 900-second token
issuer and temporary-key gateway factory, an authorization-consumption marker,
strict credential response validation, expiry/fingerprint-only evidence,
Clash listener and proxy-environment preflight, a new run/evidence boundary,
sanitized provider error persistence, and atomic legacy pre-provider failure
reconciliation.

The abandoned local proxy-failure database was verified to contain no provider,
model, request ID, usage, cost, or output evidence and was reconciled to
`FAILED` / `FAILED_TERMINAL` with `LOCAL_PROXY_PREFLIGHT_FAILED`. The renewed
live request remains unauthorized until the implementation is committed and
the Human Governor separately approves that full commit SHA.

The locked dependency check, Ruff lint and format check, Mypy, all 89 Pytest
tests, and `git diff --check` passed on 2026-08-23. No live provider request was
made during implementation or verification.
