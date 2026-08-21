# Gate C — Qwen Tokyo Guarded Live Verification Authorization

- Authorization ID: `20260821-gate-c-qwen-live-verification`
- Status: `approved` (implementation ready offline; live requests not yet started)
- Date prepared: 2026-08-21
- Date approved: 2026-08-21 by Human Governor
- Parent proposal: `20260821-phase-2-provider-verification`
- Decision owner: Human Governor
- Executor after approval: Codex

## Decision requested

Approve one tightly bounded live capability probe followed, only if the probe
passes, by one synthetic public architecture review through Alibaba Cloud Model
Studio in Tokyo. Approval authorizes the exact envelope, limits, endpoint class,
credential mechanism, execution window, and retention policy below. It does not
authorize repository source, internal data, retries, additional models, tools,
web search, prompt caching, deployment, or recurring execution.

Approval authorizes execution only when every preflight condition below passes
and the authorized window is open. As of approval-day implementation, no
credential has been read and no provider request has been made.

## Approved provider boundary

| Field | Approved Gate C value |
|---|---|
| Provider | Alibaba Cloud Model Studio / Qwen |
| Region and deployment scope | Japan (Tokyo), Global |
| Endpoint | `https://{DASHSCOPE_WORKSPACE_ID}.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions` |
| Endpoint validation | HTTPS only; exact path; host must end in `.ap-northeast-1.maas.aliyuncs.com`; no query string or alternate host |
| Logical alias | `architect_primary_v1` |
| Physical model | `qwen3.7-max-2026-05-20` |
| Provider policy | `qwen-tokyo-public-v1` |
| Data class | `PUBLIC` only |
| Thinking | `enable_thinking: false` |
| Output mode | Plain JSON object plus local Pydantic validation; no claim of provider-enforced JSON Schema |
| Tools and web search | Disabled; no tool definitions supplied |
| Streaming | Disabled |
| Prompt/session cache | Disabled; no cache header or prior response ID |
| Provider inference logging | Must be confirmed disabled in the console before execution |

The Human Governor additionally approved three implementation prerequisites:

1. provider capability declarations split JSON mode, provider-enforced JSON
   Schema, and local schema validation into separate fields;
2. provider-originated output models use strict Pydantic validation with
   `extra="forbid"`;
3. every Qwen response must include `finish_reason="stop"`; `length`, a missing
   value, or any other value is terminal and cannot advance the run.

These are fail-closed implementation controls, not additional provider
capabilities. The pinned Qwen model is recorded as supporting JSON mode with
local validation, while provider-enforced JSON Schema remains false.

The exact workspace-specific hostname is resolved locally from
`DASHSCOPE_WORKSPACE_ID`. The plaintext workspace ID is not committed. Before the
first request, the executor records the resolved endpoint hash locally and
proves that it satisfies the approved Tokyo host constraint. A missing or
non-matching value blocks execution.

## Frozen public corpus and permitted egress

The only approved corpus is
`tests/fixtures/gate_c_qwen_public_corpus.json`.

| Evidence | SHA-256 |
|---|---|
| Raw corpus file, 1,455 bytes | `5733080e2e3453bfa4520be507309529774acee9bacc1ccfeff967a0c6b10bad` |
| Canonical review envelope | `5d559b9159da3e6943a872e72cea6feff10cfa2800b9cf54e4d555ded5165734` |
| Static section | `45c6b879a391cf4ccd4c0b689096365c6bd9beb889b4a615f761a362722d6a7d` |
| Context section | `922036d1b0d14af0949d5a83c12cc91d6c885e3989a9122bd8b9eb35ac6893ec` |
| Dynamic section | `353795207c7b004a90fd61c340614612cc783893a6b9b699cc79d6e664d52b9a` |
| Local policy metadata | `7551707bad086b05661f2ed8234860fcec72a005223ef30a7f7e25bf89e9257e` |

The provider may receive only:

1. the exact capability-probe `system` and `user` strings in the frozen file;
2. the exact review envelope's `static_prefix`, JSON-serialized
   `project_context`, and `dynamic_payload`, joined by the fixed adapter delimiter
   `Project context (untrusted JSON evidence):`;
3. the approved model ID and protocol parameters required for those calls.

Local policy metadata and hashes remain local. No repository file, Git metadata,
absolute path, username, email address, credential, runtime log, or prior model
response may be added. Any byte change to the corpus or canonical envelope
invalidates this authorization.

## Call, token, time, and spend limits

| Limit | Proposed value |
|---|---:|
| Logical operations | 2 maximum: one probe, then one review |
| Physical provider requests | 2 maximum total |
| Attempts per operation | 1; no automatic or manual retry under this authorization |
| Capability-probe output | 256 tokens maximum |
| Review output | 1,792 tokens maximum |
| Aggregate provider-reported input | 3,000 tokens maximum |
| Aggregate provider-reported output | 2,048 tokens maximum |
| Aggregate provider-reported tokens | 5,048 tokens maximum |
| Wall-clock execution | 10 minutes maximum |
| Provider list-price ceiling | USD 0.02 maximum |
| Internal hard budget | RMB 0.20 maximum |

The pricing snapshot is `alibaba-model-pricing-2026-07-15`: USD 1.65 per
million input tokens and USD 4.951 per million output tokens for the pinned model
in Tokyo. At the approved token ceilings, the list-price estimate is USD
0.015089648. The USD 0.02 ceiling leaves limited rounding headroom and ignores
promotional discounts. The RMB 0.20 hard budget uses a deliberately conservative
internal planning factor of RMB 10 per USD; it is a governance ceiling, not an
exchange-rate claim.

Every started request counts against the two-request and spend ceilings even if
it times out or the billing outcome is unknown. Unknown pricing, usage, or
currency conversion blocks an additional request rather than being treated as
zero.

## Credential and console prerequisites

The Human Governor supplies values locally; neither value is pasted into chat,
written to a tracked file, SQLite, an artifact, or a routine log.

- `DASHSCOPE_API_KEY`: a dedicated pay-as-you-go key with Custom access limited
  to `qwen3.7-max-2026-05-20` and the executor's current public IP where the
  console supports it;
- `DASHSCOPE_WORKSPACE_ID`: the Tokyo workspace identifier used only to build
  the approved hostname.

Before execution, the Human Governor confirms the Tokyo region, Custom model/IP
scope, provider inference logging disabled, and billing access. The key is
disabled, reset, or deleted immediately after the evidence reconciliation, and
immediately on suspected exposure. Failure to confirm any prerequisite blocks
the test.

## Execution sequence

1. Verify a clean approved implementation commit and rerun the complete offline
   suite.
2. Recompute the raw corpus and canonical envelope hashes and run the egress
   scanners. A mismatch or scanner finding stops the run.
3. Validate the environment variables without printing their values. Validate
   and hash the resolved endpoint locally.
4. Reserve the full RMB 0.20 hard budget before any provider request.
5. Send the JSON capability probe with `enable_thinking: false` and a 256-token
   output cap.
6. Require HTTP success, the pinned physical model identity, safe request ID,
   usage fields, and valid JSON exactly matching `{"status":"ok"}`.
7. Only after step 6 passes, send the frozen review envelope with a 1,792-token
   output cap.
8. Validate the response locally, persist the physical attempt and safe provider
   evidence, reconcile SQLite/artifacts/logs, and compare usage with the provider
   dashboard when available.
9. Disable, reset, or delete the dedicated key and publish a redacted verification
   record for Human Governor review.

## Stop conditions

Stop before the next request when any of the following occurs:

- corpus, envelope, implementation commit, alias, model, policy, endpoint, or
  pricing snapshot differs from this authorization;
- the egress scanner detects a secret, PII, prompt-injection marker, non-public
  data, or scanner error;
- a credential or workspace value is missing, exposed, printed, or rejected;
- the endpoint fails the Tokyo allowlist check;
- the capability probe returns a different model, invalid JSON, schema mismatch,
  missing usage/request evidence, timeout, authentication error, throttle, or
  any non-success status;
- a token, attempt, request, time, USD, or RMB ceiling would be exceeded;
- provider caching, tools, web search, inference logging, streaming, or thinking
  is observed or cannot be ruled out;
- SQLite, artifact, and structured-log evidence cannot be reconciled.

No failure under this authorization is retryable. A new request after any stop
condition requires a new Human Governor approval.

## Execution window and retention

- Authorized execution window: 2026-08-22 09:00 through 2026-08-28 21:00 JST.
- The authorization expires unused at the end of that window.
- Local redacted evidence may be retained for 30 calendar days after execution.
- The Human Governor owns deletion at expiry. Codex may prepare the exact
  deletion inventory but does not delete evidence without a separate instruction.
- Credentials are not retained. Provider-side payload retention remains unknown;
  this residual risk is accepted only for the frozen synthetic PUBLIC corpus.

## Security/Ops review

Classification: **required; implementation review complete, execution preflight
pending**. The approved runner limits egress to synthetic public material, fails
closed on drift, forbids retries, validates `finish_reason`, and caps spend.
Residual risks are provider-side retention uncertainty, ambiguous billing after
timeout, ordinary internet transport risk, and the possibility that the pinned
model supports JSON mode less reliably than expected.

Alibaba Cloud documentation states that call data is not used for model
training, but it does not provide a sufficiently precise API payload-retention
period for this decision. The model information page also marks schema-enforced
Structured Outputs as unsupported. Gate C therefore tests only plain JSON mode
with local validation and stops before the review if that probe fails.

## Validation and done criteria

Gate C is complete only when:

1. the offline suite passes immediately before execution;
2. corpus, envelope, endpoint, alias, model, and policy hashes match;
3. no more than two provider requests occur and no retry occurs;
4. the probe and review either pass in sequence or produce a correctly governed
   stopped/partial result;
5. usage, request IDs, model identity, latency, price provenance, SQLite,
   artifacts, and redacted logs reconcile;
6. no credential or prohibited content appears in tracked or runtime evidence;
7. the dedicated key is disabled, reset, or deleted;
8. the final verification record states actual usage/cost, residual risks, and
   whether Phase 2 may move from `implemented` to `verified`.

## State transitions

- Current: `approved`; implementation is ready offline and no live request has
  started.
- Exact Human Governor approval recorded: 2026-08-21.
- When the first authorized provider request starts: `in_progress`.
- After reconciliation and key revocation: `verified` or `blocked`, according to
  evidence.
- Expired without execution: `blocked` pending a refreshed authorization window.

## Sources

- Alibaba Cloud Model Studio, [regional endpoints and model
  service](https://www.alibabacloud.com/help/en/model-studio/what-is-model-studio),
  last updated 2026-07-10.
- Alibaba Cloud Model Studio, [model inference
  pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing), last
  updated 2026-07-15.
- Alibaba Cloud Model Studio, [qwen3.7-max model
  information](https://www.alibabacloud.com/help/en/model-studio/qwen3-7-max),
  last updated 2026-07-24.
- Alibaba Cloud Model Studio, [deep thinking mode
  controls](https://www.alibabacloud.com/help/en/model-studio/deep-thinking), last
  updated 2026-07-15.
- Alibaba Cloud Model Studio, [API key creation and
  management](https://www.alibabacloud.com/help/en/model-studio/get-api-key), last
  updated 2026-07-14.
- Alibaba Cloud Model Studio, [security certifications and
  privacy](https://www.alibabacloud.com/help/en/model-studio/privacy-notice), last
  updated 2026-05-15.

## Approval wording

To approve the exact envelope and limits above, reply:

> 批准 Gate C（Qwen Tokyo，按 20260821-gate-c-qwen-live-verification 提案）

Any requested change to corpus, endpoint class, model, limits, window, or
retention returns this authorization to draft for re-hashing and review.
