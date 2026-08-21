# Gate C — Qwen Beijing Guarded Live Verification Authorization

- Authorization ID: `20260822-gate-c-qwen-beijing-live-verification`
- Status: `implemented` (approved and verified offline; no live request made)
- Date approved: 2026-08-22 by Human Governor
- Parent proposal: `20260821-phase-2-provider-verification`
- Supersedes: `20260821-gate-c-qwen-live-verification`
- Decision owner: Human Governor
- Executor after clean-commit approval: Codex

## Background

The Tokyo Gate C packet was approved and implemented offline, but no provider
request was made. A real account constraint requires the Alibaba Cloud China
site and Model Studio China (Beijing), region ID `cn-beijing`. The Human Governor
approved changing only this provider location while preserving the pinned model,
synthetic public workload, call limits, no-retry rule, budget, window, and local
retention boundary.

The Tokyo packet remains as a superseded audit record. Its authorization ID,
endpoint, policy version, pricing, and corpus hashes cannot be used for Beijing.

## Purpose

Authorize one fail-closed JSON capability probe and, only if it passes, one
synthetic public architecture review through the Beijing workspace-specific
OpenAI-compatible endpoint.

## Scope

| Field | Approved Beijing value |
|---|---|
| Provider | 阿里云百炼 / Alibaba Cloud Model Studio China |
| Region | China (Beijing), `cn-beijing` |
| Endpoint | `https://{DASHSCOPE_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions` |
| Endpoint validation | HTTPS; exact compatible-mode path; host suffix `.cn-beijing.maas.aliyuncs.com`; no query or alternate host |
| Logical alias | `architect_primary_v1` |
| Physical model | `qwen3.7-max-2026-05-20` |
| Provider policy | `qwen-beijing-public-v1` |
| Data class | Synthetic `PUBLIC` only |
| Output contract | JSON Object plus strict local Pydantic validation |
| Thinking | `enable_thinking: false` |
| Tools, web, streaming | Disabled; no tool definitions; non-streaming |
| Prompt cache | Disabled; observed cache usage stops the run |
| Inference logs | Must be confirmed disabled before execution |

The checked-in provider policy remains `network_enabled: false`. Only the
dedicated Gate C runner constructs a temporary in-memory allow policy after all
preflight checks pass.

## Frozen corpus and permitted egress

The approved corpus remains the same synthetic probe and review content at
`tests/fixtures/gate_c_qwen_public_corpus.json`. Only its local provider policy
metadata changed from Tokyo to Beijing, requiring new integrity hashes.

| Evidence | SHA-256 |
|---|---|
| Raw corpus, 1,457 bytes | `b75768802f6ae6a93829cdd035e5a8f1ace2294bc2400902d4944029ec32c9a0` |
| Canonical review envelope | `7eb5638022bff718f1f9f70b59197c54dcdfb708178336f738f330de7524ee15` |
| Static section | `45c6b879a391cf4ccd4c0b689096365c6bd9beb889b4a615f761a362722d6a7d` |
| Context section | `922036d1b0d14af0949d5a83c12cc91d6c885e3989a9122bd8b9eb35ac6893ec` |
| Dynamic section | `353795207c7b004a90fd61c340614612cc783893a6b9b699cc79d6e664d52b9a` |
| Policy section | `95e07e5483ec68ca87a80f1c4b9e70670c40f4956b196c405cd9eb1f30328683` |

The provider may receive only the frozen probe strings and the frozen review
system prompt, fixed untrusted-context delimiter, JSON-serialized public sample,
and proposal. No repository source, path, Git data, username, email, credential,
runtime evidence, or prior response may be added.

## Limits and pricing

| Limit | Approved value |
|---|---:|
| Logical operations | 2 maximum: probe, then conditional review |
| Physical requests | 2 maximum total |
| Attempts | 1 per operation; no retry or repair |
| Probe output | 256 tokens maximum |
| Review output | 1,792 tokens maximum |
| Aggregate input | 3,000 tokens maximum |
| Aggregate output | 2,048 tokens maximum |
| Wall clock | 10 minutes maximum |
| Internal hard budget | RMB 0.20 |
| Existing planning ceiling | USD 0.02 equivalent at the approved conservative factor |

Pricing snapshot `alibaba-model-pricing-cn-beijing-2026-08-22` uses the official
Beijing list price of RMB 12 per million input tokens and RMB 36 per million
output tokens. At the approved limits, maximum list-price cost is RMB 0.109728.
Promotions and free quota are ignored. Unknown or inconsistent usage blocks the
next request.

## Credential and console prerequisites

- Use an aliyun.com Model Studio API key created in `cn-beijing`.
- Use the Beijing Workspace ID only to form the approved hostname.
- Select Custom key permissions and restrict access to
  `qwen3.7-max-2026-05-20` and the executor's public IP.
- Confirm model permission, billing access, and inference logs disabled.
- Supply `DASHSCOPE_API_KEY` and `DASHSCOPE_WORKSPACE_ID` only in the local
  process environment; never print, chat, commit, or persist their values.
- Disable, reset, or delete the dedicated key immediately after reconciliation
  or suspected exposure.

## Non-goals

- No Tokyo, international, trial, or generic DashScope endpoint.
- No non-public data, repository source, additional model, fallback, retry,
  repair, tools, search, cache, streaming, deployment, or recurring job.
- No switch to Responses API or provider-enforced JSON Schema in this run.
- No change to blind-review ownership or target-repository write permissions.

## Proposed approach

Keep the existing `QwenModelGateway` and Gate C runner interfaces. Replace the
single approved endpoint suffix and region constants, update capability evidence
for Beijing, use native RMB pricing, and bind the runner to a new authorization
ID and policy version. This keeps regional knowledge local to the adapter and
Gate C boundary rather than spreading conditionals through orchestration.

## Alternatives considered

- Support Tokyo and Beijing simultaneously: rejected because it broadens egress
  and makes an accidentally wrong-region call possible.
- Use generic `dashscope.aliyuncs.com`: rejected because the approved boundary
  requires a workspace-specific hostname.
- Switch to Responses API: deferred; Chat Completions supports the approved text
  and JSON Object workflow and avoids changing the request contract.
- Enable JSON Schema: deferred despite Beijing support; strict local validation
  preserves the already approved behavior.

## Implementation steps

1. Test first that Beijing endpoints are accepted and Tokyo endpoints rejected.
2. Update provider config, adapter region evidence, and pricing snapshot.
3. Update Gate C policy, authorization ID, native RMB cost calculation, corpus
   policy metadata, and integrity hashes.
4. Preserve and supersede the Tokyo authorization record.
5. Synchronize README, Security/Ops, decisions, tasks, and parent proposal.
6. Run the complete offline suite and sensitive-data scan.
7. Commit the implementation and separately use that clean full SHA at live
   preflight; no request is authorized from a dirty or different commit.

## Ownership and affected paths

- Adapter/config: `src/model_council/adapters/qwen.py`, `config/`
- Gate runner/CLI: `src/model_council/gate_c.py`, `src/model_council/cli.py`
- Frozen evidence/tests: `tests/fixtures/`, `tests/test_gate_c_*`, provider tests
- Governance/docs: `proposals/active/`, `README.md`, `docs/SECURITY.md`,
  `DECISIONS.md`, `TASKS.md`

## Security/Ops classification

**Required and approved for implementation; execution preflight pending.** The
region, account platform, hostname trust boundary, key, data residency, and
pricing source changed. Synthetic public data and strict stop conditions bound
the residual provider-side retention and transport risks.

## Risks and mitigations

- Wrong-region egress: exact Beijing suffix/path validation; Tokyo is rejected.
- China/international key mismatch: require a Beijing workspace key and stop on
  authentication failure without retry.
- Pricing drift: pinned native-CNY snapshot and RMB 0.20 reservation.
- Capability drift: probe JSON mode, physical model, request ID, usage, cache,
  and finish reason before review.
- Logging or retention: inference logs confirmed disabled; payload retention
  remains unknown, so only frozen synthetic public data is permitted.
- Ambiguous timeout/billing: terminal stop; no second request.

## Validation plan

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
git diff --check
```

Focused tests prove endpoint allow/deny behavior, config drift rejection, corpus
hashes, probe-before-review ordering, model/request/usage/cache checks, two-call
ceiling, native RMB cost, zero retry, and authorization window enforcement.

## Done criteria

1. Beijing implementation is committed from a fully green, clean worktree.
2. The Human Governor names the full implementation SHA as the live baseline.
3. Console prerequisites are confirmed without disclosing credentials.
4. At most two requests run sequentially and all evidence reconciles.
5. Actual cost is within RMB 0.20 and billing evidence is reviewed.
6. The dedicated key is revoked and the redacted verification record is reviewed.

## State transition plan

- Current: `implemented` — exact migration verified offline; no live request made.
- After offline implementation and verification: `implemented`.
- When the first approved Beijing request starts: live execution `in_progress`.
- After evidence reconciliation and key revocation: `verified` or `blocked`.
- Expired unused after 2026-08-28 21:00 JST: `blocked` pending renewed approval.

## Execution window and retention

- Window: 2026-08-22 09:00 through 2026-08-28 21:00 JST.
- Local redacted evidence: 30 calendar days maximum.
- Human Governor owns deletion; credentials are never retained.

## Authoritative sources

- https://help.aliyun.com/zh/model-studio/regions/
- https://help.aliyun.com/zh/model-studio/qwen3-7-max
- https://help.aliyun.com/zh/model-studio/qwen-structured-output
- https://help.aliyun.com/zh/model-studio/model-pricing
- https://help.aliyun.com/zh/model-studio/get-api-key

## Approval record

The Human Governor approved this exact change on 2026-08-22:

> 确定只改变为 Alibaba Cloud 中国站（aliyun.com）Model Studio 北京区域
> cn-beijing，其余的继续沿用原方案
