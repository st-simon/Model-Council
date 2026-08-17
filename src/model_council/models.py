from __future__ import annotations

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
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INVALID = "INVALID"


class ModelCallError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class InvalidStateTransition(RuntimeError):
    pass


class ReviewInput(BaseModel):
    project_id: str
    run_id: str
    proposal: str
    context: dict[str, str] = Field(default_factory=dict)
    reviewers: list[str]
    minimum_successful_reviewers: int = 1

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
    prompt: str
    context: dict[str, str]


class GatewayResponse(BaseModel):
    raw_output: str
    provider: str
    actual_model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_rmb: float = 0.0


class Finding(BaseModel):
    category: str
    raw_severity: str
    claim: str
    recommendation: str


class ReviewOutput(BaseModel):
    reviewer: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)


class StoredCall(BaseModel):
    role: str
    status: CallStatus
    prompt_hash: str
    context_hash: str
    output: ReviewOutput | None = None
    error_code: str | None = None
    provider: str | None = None
    actual_model_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_rmb: float | None = None


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
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_rmb: float | None = None
    status: CallStatus
    error_code: str | None = None
