from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


def _safe_identifier(value: str) -> str:
    if ".." in value or SAFE_IDENTIFIER.fullmatch(value) is None:
        raise ValueError("identifier contains unsafe path characters")
    return value


class RunState(StrEnum):
    INITIALIZED = "INITIALIZED"
    BLIND_REVIEW_RUNNING = "BLIND_REVIEW_RUNNING"
    BLIND_REVIEW_DONE = "BLIND_REVIEW_DONE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CallStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    INVALID = "INVALID"


class AttemptStatus(StrEnum):
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    TIMED_OUT = "TIMED_OUT"
    INVALID = "INVALID"
    FAILED_TERMINAL = "FAILED_TERMINAL"


class AttemptKind(StrEnum):
    REVIEW = "REVIEW"
    REPAIR = "REPAIR"


class CallErrorKind(StrEnum):
    TRANSIENT = "TRANSIENT"
    THROTTLED = "THROTTLED"
    TIMEOUT = "TIMEOUT"
    AUTHENTICATION = "AUTHENTICATION"
    POLICY = "POLICY"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    PERMANENT = "PERMANENT"


class ModelCallError(RuntimeError):
    def __init__(
        self, code: str, kind: CallErrorKind = CallErrorKind.PERMANENT
    ) -> None:
        super().__init__(code)
        self.code = code
        self.kind = kind

    @property
    def retryable(self) -> bool:
        return self.kind in {
            CallErrorKind.TRANSIENT,
            CallErrorKind.THROTTLED,
            CallErrorKind.TIMEOUT,
        }


class InvalidStateTransition(RuntimeError):
    pass


class BudgetPolicy(BaseModel):
    soft_limit_rmb: float | None = Field(default=None, ge=0)
    hard_limit_rmb: float | None = Field(default=None, ge=0)
    estimated_call_cost_rmb: float = Field(default=0.0, ge=0)
    max_output_tokens: int = Field(default=4096, gt=0)

    @model_validator(mode="after")
    def validate_limits(self) -> BudgetPolicy:
        if (
            self.soft_limit_rmb is not None
            and self.hard_limit_rmb is not None
            and self.soft_limit_rmb > self.hard_limit_rmb
        ):
            raise ValueError("soft budget cannot exceed hard budget")
        return self


class PolicyMetadata(BaseModel):
    data_class: str
    provider_policy_version: str
    prompt_version: str


class PromptEnvelope(BaseModel):
    static_prefix: str
    project_context: dict[str, str] = Field(default_factory=dict)
    dynamic_payload: str
    policy_metadata: PolicyMetadata

    @staticmethod
    def _hash(value: object) -> str:
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @property
    def static_hash(self) -> str:
        return self._hash(self.static_prefix)

    @property
    def context_hash(self) -> str:
        return self._hash(self.project_context)

    @property
    def dynamic_hash(self) -> str:
        return self._hash(self.dynamic_payload)

    @property
    def policy_hash(self) -> str:
        return self._hash(self.policy_metadata.model_dump(mode="json"))

    @property
    def section_hashes(self) -> dict[str, str]:
        return {
            "static": self.static_hash,
            "context": self.context_hash,
            "dynamic": self.dynamic_hash,
            "policy": self.policy_hash,
        }

    @property
    def envelope_hash(self) -> str:
        return self._hash(self.model_dump(mode="json"))


class ReviewInput(BaseModel):
    project_id: str
    run_id: str
    proposal: str
    context: dict[str, str] = Field(default_factory=dict)
    reviewers: list[str]
    minimum_successful_reviewers: int = 1
    max_provider_attempts: int = Field(default=2, ge=1, le=5)
    budget: BudgetPolicy = Field(default_factory=BudgetPolicy)

    @field_validator("project_id", "run_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _safe_identifier(value)

    @field_validator("reviewers")
    @classmethod
    def validate_reviewer_aliases(cls, values: list[str]) -> list[str]:
        return [_safe_identifier(value) for value in values]

    @model_validator(mode="after")
    def validate_quorum(self) -> ReviewInput:
        if not self.reviewers:
            raise ValueError("at least one reviewer is required")
        if not 1 <= self.minimum_successful_reviewers <= len(self.reviewers):
            raise ValueError("reviewer quorum must be within the reviewer count")
        if len(set(self.reviewers)) != len(self.reviewers):
            raise ValueError("reviewer aliases must be unique")
        return self


class GatewayRequest(BaseModel):
    project_id: str
    run_id: str
    role: str
    model_alias: str | None = None
    prompt: str
    context: dict[str, str]
    envelope: PromptEnvelope | None = None
    max_output_tokens: int = Field(default=4096, gt=0)


class ProviderCapabilities(BaseModel):
    provider: str
    model_alias: str
    actual_model_id: str
    structured_output: bool
    prompt_cache: bool = False
    cache_min_prefix_tokens: int | None = None
    usage_reporting: bool = False
    request_id_reporting: bool = False
    max_context_tokens: int | None = None
    max_output_tokens: int | None = None
    region: str | None = None
    endpoint_class: str | None = None
    pricing_snapshot_id: str | None = None
    network_call_performed: bool = False


class ModelVerification(BaseModel):
    model_alias: str
    provider: str
    actual_model_id: str
    compatible: bool
    missing_capabilities: list[str] = Field(default_factory=list)
    network_call_performed: bool


class GatewayResponse(BaseModel):
    raw_output: str
    provider: str
    actual_model_id: str
    input_tokens: int
    uncached_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    output_tokens: int
    latency_ms: int
    cost_rmb: float | None = None
    provider_request_id: str | None = None
    pricing_snapshot_id: str | None = None


class Finding(BaseModel):
    category: str
    raw_severity: str
    claim: str
    recommendation: str


class RadicalChallenge(BaseModel):
    evidence: str = Field(min_length=1)
    minimal_alternative: str = Field(min_length=1)
    trade_off: str = Field(min_length=1)
    residual_risk: str = Field(min_length=1)


class ReviewOutput(BaseModel):
    reviewer: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    radical_challenges: list[RadicalChallenge] = Field(default_factory=list)


class StoredCall(BaseModel):
    role: str
    model_alias: str | None = None
    status: CallStatus
    prompt_hash: str
    context_hash: str
    output: ReviewOutput | None = None
    error_code: str | None = None
    provider: str | None = None
    actual_model_id: str | None = None
    input_tokens: int | None = None
    uncached_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_rmb: float | None = None
    provider_request_id: str | None = None
    pricing_snapshot_id: str | None = None


class StoredAttempt(BaseModel):
    attempt_id: int
    role: str
    ordinal: int
    kind: AttemptKind
    status: AttemptStatus
    error_code: str | None = None
    provider: str | None = None
    actual_model_id: str | None = None
    input_tokens: int | None = None
    uncached_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_rmb: float | None = None
    provider_request_id: str | None = None
    pricing_snapshot_id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    next_retry_at: datetime | None = None


class RunSummary(BaseModel):
    run_id: str
    state: RunState
    successful_reviewers: list[str]
    failed_reviewers: list[str]
    partial_review: bool
    report_path: Path


class CallLogEvent(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str
    role: str
    model_alias: str
    actual_model_id: str | None = None
    provider: str | None = None
    prompt_hash: str
    context_hash: str
    input_tokens: int | None = None
    uncached_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_rmb: float | None = None
    provider_request_id: str | None = None
    pricing_snapshot_id: str | None = None
    status: CallStatus
    error_code: str | None = None
