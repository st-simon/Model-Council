from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic

from pydantic import BaseModel, ConfigDict

from model_council.adapters.qwen import PRICING_SNAPSHOT_ID, QwenModelGateway
from model_council.configuration import ProviderConfig
from model_council.egress import EgressGuard
from model_council.models import (
    AttemptKind,
    AttemptStatus,
    BudgetPolicy,
    CallLogEvent,
    CallStatus,
    GatewayRequest,
    GatewayResponse,
    JsonModeProbeOutput,
    ModelCallError,
    PolicyMetadata,
    PromptEnvelope,
    ReviewInput,
    ReviewOutput,
    RunState,
)
from model_council.ports import ArtifactStore, RunStore

AUTHORIZATION_ID = "20260823-gate-c-qwen-beijing-temporary-key-renewal"
CORPUS_SHA256 = "b75768802f6ae6a93829cdd035e5a8f1ace2294bc2400902d4944029ec32c9a0"
ENVELOPE_SHA256 = "7eb5638022bff718f1f9f70b59197c54dcdfb708178336f738f330de7524ee15"
MODEL_ALIAS = "architect_primary_v1"
MODEL_ID = "qwen3.7-max-2026-05-20"
POLICY_VERSION = "qwen-beijing-public-v1"
WINDOW_START = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)  # 09:00 JST
WINDOW_END = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)  # 21:00 JST
INPUT_TOKEN_LIMIT = 3_000
OUTPUT_TOKEN_LIMIT = 2_048
PHYSICAL_REQUEST_LIMIT = 2
PROBE_OUTPUT_LIMIT = 256
REVIEW_OUTPUT_LIMIT = 1_792
WALL_CLOCK_LIMIT_SECONDS = 600.0
HARD_BUDGET_RMB = 0.20
INPUT_RMB_PER_MILLION = 12.0
OUTPUT_RMB_PER_MILLION = 36.0


class GateCStopped(RuntimeError):
    pass


class ProbeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    system: str
    user: str
    expected: JsonModeProbeOutput


class GateCCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    corpus_id: str
    data_class: str
    capability_probe: ProbeSpec
    review_envelope: PromptEnvelope


class GateCResult(BaseModel):
    authorization_id: str
    run_id: str
    state: RunState
    physical_requests: int
    input_tokens: int
    output_tokens: int
    cost_rmb: float
    report_path: Path
    key_revocation_required: bool = True


def gate_c_policy() -> ProviderConfig:
    return ProviderConfig(
        network_enabled=True,
        allowed_data_classes=["PUBLIC"],
        region="cn-beijing",
        training_use="provider_states_not_used_for_training",
        payload_retention="unknown",
        inference_logging_enabled=False,
        prompt_cache_enabled=False,
    )


def probe_envelope(spec: ProbeSpec) -> PromptEnvelope:
    return PromptEnvelope(
        static_prefix=spec.system,
        dynamic_payload=spec.user,
        policy_metadata=PolicyMetadata(
            data_class="PUBLIC",
            provider_policy_version=POLICY_VERSION,
            prompt_version="gate-c-json-probe-v1",
        ),
    )


def load_gate_c_corpus(
    corpus_path: Path, guard: EgressGuard | None = None
) -> GateCCorpus:
    raw = corpus_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CORPUS_SHA256:
        raise GateCStopped("CORPUS_HASH_MISMATCH")
    corpus = GateCCorpus.model_validate_json(raw)
    if corpus.data_class != "PUBLIC":
        raise GateCStopped("DATA_CLASS_DENIED")
    if corpus.review_envelope.envelope_hash != ENVELOPE_SHA256:
        raise GateCStopped("ENVELOPE_HASH_MISMATCH")
    policy_version = corpus.review_envelope.policy_metadata.provider_policy_version
    if policy_version != POLICY_VERSION:
        raise GateCStopped("POLICY_VERSION_MISMATCH")
    active_guard = guard or EgressGuard()
    policy = gate_c_policy()
    active_guard.authorize(
        probe_envelope(corpus.capability_probe), "qwen_model_studio", policy
    )
    active_guard.authorize(corpus.review_envelope, "qwen_model_studio", policy)
    return corpus


class GateCRunner:
    def __init__(
        self,
        *,
        gateway: QwenModelGateway,
        run_store: RunStore,
        artifact_store: ArtifactStore,
        guard: EgressGuard | None = None,
        now: datetime | None = None,
        credential_expires_at: datetime,
    ) -> None:
        self.gateway = gateway
        self.run_store = run_store
        self.artifact_store = artifact_store
        self.guard = guard or EgressGuard()
        self.now = now or datetime.now(UTC)
        self.credential_expires_at = credential_expires_at
        self.policy = gate_c_policy()
        self.responses: list[GatewayResponse] = []

    async def execute(self, corpus_path: Path) -> GateCResult:
        started = monotonic()
        corpus = load_gate_c_corpus(corpus_path, self.guard)
        self._check_window()
        self._check_credential_lifetime()
        run_id = "R-GATE-C-QWEN-BEIJING-002"
        review_input = ReviewInput(
            project_id="gate-c-qwen-beijing-public",
            run_id=run_id,
            proposal=corpus.review_envelope.dynamic_payload,
            context=corpus.review_envelope.project_context,
            reviewers=["capability_probe", "architect"],
            minimum_successful_reviewers=2,
            max_provider_attempts=1,
            max_schema_repairs=0,
            budget=BudgetPolicy(
                hard_limit_rmb=HARD_BUDGET_RMB,
                estimated_call_cost_rmb=HARD_BUDGET_RMB,
                max_output_tokens=REVIEW_OUTPUT_LIMIT,
            ),
        )
        state = self.run_store.create_or_load(review_input)
        if state != RunState.INITIALIZED or self.run_store.list_calls(run_id):
            raise GateCStopped("GATE_C_ALREADY_ATTEMPTED")
        self.run_store.transition(run_id, RunState.BLIND_REVIEW_RUNNING)
        if not self.run_store.reserve_budget(run_id, HARD_BUDGET_RMB, HARD_BUDGET_RMB):
            self._fail_run(run_id)
            raise GateCStopped("BUDGET_HARD_LIMIT")

        try:
            await self._run_probe(review_input, corpus)
            self._check_wall_clock(started)
            await self._run_review(review_input, corpus.review_envelope)
            self._check_wall_clock(started)
        except GateCStopped:
            self._fail_run(run_id)
            raise

        self.run_store.transition(run_id, RunState.BLIND_REVIEW_DONE)
        self.run_store.transition(run_id, RunState.COMPLETED)
        calls = self.run_store.list_calls(run_id)
        report_path = self.artifact_store.write_report(
            review_input, RunState.COMPLETED, calls
        )
        return GateCResult(
            authorization_id=AUTHORIZATION_ID,
            run_id=run_id,
            state=RunState.COMPLETED,
            physical_requests=len(self.responses),
            input_tokens=sum(item.input_tokens for item in self.responses),
            output_tokens=sum(item.output_tokens for item in self.responses),
            cost_rmb=sum(item.cost_rmb or 0.0 for item in self.responses),
            report_path=report_path,
        )

    def _check_window(self) -> None:
        if not WINDOW_START <= self.now <= WINDOW_END:
            raise GateCStopped("AUTHORIZATION_WINDOW_CLOSED")

    def _check_credential_lifetime(self) -> None:
        remaining = self.credential_expires_at - self.now
        if not (
            timedelta(seconds=WALL_CLOCK_LIMIT_SECONDS)
            <= remaining
            <= timedelta(seconds=900)
        ):
            raise GateCStopped("TEMPORARY_KEY_LIFETIME_TOO_SHORT")

    async def _run_probe(self, review_input: ReviewInput, corpus: GateCCorpus) -> None:
        spec = corpus.capability_probe
        envelope = probe_envelope(spec)
        request = GatewayRequest(
            project_id=review_input.project_id,
            run_id=review_input.run_id,
            role="capability_probe",
            model_alias=MODEL_ALIAS,
            prompt=f"{spec.system}\n{spec.user}",
            context={},
            envelope=envelope,
            max_output_tokens=PROBE_OUTPUT_LIMIT,
        )
        self.guard.authorize(envelope, "qwen_model_studio", self.policy)
        attempt_id = self._start_call(request)
        try:
            response = await self.gateway.probe_json_mode(
                model_alias=MODEL_ALIAS,
                system=spec.system,
                user=spec.user,
                max_output_tokens=PROBE_OUTPUT_LIMIT,
            )
        except ModelCallError as error:
            self._record_transport_failure(request, attempt_id, error)
            raise GateCStopped(error.code) from None
        try:
            response = self._record_physical_success(request, attempt_id, response, 0)
        except GateCStopped as error:
            self._record_invalid(request, response, str(error))
            raise
        try:
            observed = JsonModeProbeOutput.model_validate_json(response.raw_output)
        except ValueError:
            self._record_invalid(request, response, "PROBE_INVALID")
            raise GateCStopped("PROBE_INVALID") from None
        if observed != spec.expected:
            self._record_invalid(request, response, "PROBE_SCHEMA_MISMATCH")
            raise GateCStopped("PROBE_SCHEMA_MISMATCH")
        self.run_store.save_success(
            request.run_id,
            request.role,
            response,
            ReviewOutput(
                reviewer=request.role,
                summary="Approved JSON mode probe returned the expected value.",
            ),
        )
        self._write_log(request, response, CallStatus.SUCCEEDED)

    async def _run_review(
        self, review_input: ReviewInput, envelope: PromptEnvelope
    ) -> None:
        self.guard.authorize(envelope, "qwen_model_studio", self.policy)
        request = GatewayRequest(
            project_id=review_input.project_id,
            run_id=review_input.run_id,
            role="architect",
            model_alias=MODEL_ALIAS,
            prompt=envelope.static_prefix + envelope.dynamic_payload,
            context=envelope.project_context,
            envelope=envelope,
            max_output_tokens=REVIEW_OUTPUT_LIMIT,
        )
        attempt_id = self._start_call(request)
        try:
            response = await self.gateway.review(request)
        except ModelCallError as error:
            self._record_transport_failure(request, attempt_id, error)
            raise GateCStopped(error.code) from None
        try:
            response = self._record_physical_success(request, attempt_id, response, 0)
        except GateCStopped as error:
            self._record_invalid(request, response, str(error))
            raise
        try:
            output = ReviewOutput.model_validate_json(response.raw_output)
        except ValueError:
            self._record_invalid(request, response, "REVIEW_INVALID")
            raise GateCStopped("REVIEW_INVALID") from None
        if output.reviewer != "architect":
            self._record_invalid(request, response, "REVIEWER_MISMATCH")
            raise GateCStopped("REVIEWER_MISMATCH")
        self.run_store.save_success(request.run_id, request.role, response, output)
        self._write_log(request, response, CallStatus.SUCCEEDED)

    def _start_call(self, request: GatewayRequest) -> int:
        if request.envelope is None:
            raise GateCStopped("PROMPT_ENVELOPE_REQUIRED")
        existing = self.run_store.claim_call(
            request.run_id,
            request.role,
            request.model_alias or request.role,
            request.envelope.context_hash,
            request.envelope.envelope_hash,
        )
        if existing is not None:
            raise GateCStopped("GATE_C_CALL_ALREADY_EXISTS")
        self.artifact_store.write_call_input(request)
        return self.run_store.start_attempt(
            request.run_id, request.role, AttemptKind.REVIEW
        ).attempt_id

    def _record_physical_success(
        self,
        request: GatewayRequest,
        attempt_id: int,
        response: GatewayResponse,
        artifact_attempt: int,
    ) -> GatewayResponse:
        response = response.model_copy(update={"cost_rmb": self._cost_rmb(response)})
        self.run_store.finish_attempt_success(attempt_id, response)
        self.artifact_store.write_raw_output(
            request.project_id,
            request.run_id,
            request.role,
            artifact_attempt,
            response.raw_output,
        )
        self.responses.append(response)
        self._check_observed_limits(response)
        return response

    def _check_observed_limits(self, response: GatewayResponse) -> None:
        if len(self.responses) > PHYSICAL_REQUEST_LIMIT:
            raise GateCStopped("PHYSICAL_REQUEST_LIMIT")
        if response.provider != "qwen_model_studio":
            raise GateCStopped("PROVIDER_MISMATCH")
        if response.actual_model_id != MODEL_ID:
            raise GateCStopped("ACTUAL_MODEL_ID_MISMATCH")
        if response.provider_request_id is None:
            raise GateCStopped("PROVIDER_REQUEST_ID_MISSING")
        if response.pricing_snapshot_id != PRICING_SNAPSHOT_ID:
            raise GateCStopped("PRICING_SNAPSHOT_MISMATCH")
        if (response.cache_read_input_tokens or 0) > 0 or (
            response.cache_creation_input_tokens or 0
        ) > 0:
            raise GateCStopped("CACHE_OBSERVED")
        if sum(item.input_tokens for item in self.responses) > INPUT_TOKEN_LIMIT:
            raise GateCStopped("INPUT_TOKEN_LIMIT")
        if sum(item.output_tokens for item in self.responses) > OUTPUT_TOKEN_LIMIT:
            raise GateCStopped("OUTPUT_TOKEN_LIMIT")
        if sum(item.cost_rmb or 0.0 for item in self.responses) > HARD_BUDGET_RMB:
            raise GateCStopped("BUDGET_HARD_LIMIT")

    @staticmethod
    def _check_wall_clock(started: float) -> None:
        if monotonic() - started > WALL_CLOCK_LIMIT_SECONDS:
            raise GateCStopped("WALL_CLOCK_LIMIT")

    def _record_transport_failure(
        self, request: GatewayRequest, attempt_id: int, error: ModelCallError
    ) -> None:
        self.run_store.finish_attempt_failure(
            attempt_id,
            error.code,
            AttemptStatus.FAILED_TERMINAL,
            provider_error_code=error.provider_error_code,
            provider_request_id=error.provider_request_id,
        )
        self.run_store.save_failure(
            request.run_id,
            request.role,
            error.code,
            retryable=False,
            max_attempts=1,
            provider_error_code=error.provider_error_code,
            provider_request_id=error.provider_request_id,
        )
        self._write_log(
            request,
            None,
            CallStatus.FAILED_TERMINAL,
            error_code=error.code,
            provider_error_code=error.provider_error_code,
            provider_request_id=error.provider_request_id,
        )

    def _record_invalid(
        self, request: GatewayRequest, response: GatewayResponse, code: str
    ) -> None:
        self.run_store.save_invalid(request.run_id, request.role, code)
        self._write_log(request, response, CallStatus.INVALID, error_code=code)

    def _write_log(
        self,
        request: GatewayRequest,
        response: GatewayResponse | None,
        status: CallStatus,
        *,
        error_code: str | None = None,
        provider_error_code: str | None = None,
        provider_request_id: str | None = None,
    ) -> None:
        envelope = request.envelope
        if envelope is None:
            raise GateCStopped("PROMPT_ENVELOPE_REQUIRED")
        self.artifact_store.write_call_log(
            CallLogEvent(
                run_id=request.run_id,
                role=request.role,
                model_alias=request.model_alias or request.role,
                actual_model_id=response.actual_model_id if response else None,
                provider=response.provider if response else None,
                prompt_hash=envelope.envelope_hash,
                context_hash=envelope.context_hash,
                input_tokens=response.input_tokens if response else None,
                uncached_input_tokens=(
                    response.uncached_input_tokens if response else None
                ),
                cache_creation_input_tokens=(
                    response.cache_creation_input_tokens if response else None
                ),
                cache_read_input_tokens=(
                    response.cache_read_input_tokens if response else None
                ),
                output_tokens=response.output_tokens if response else None,
                latency_ms=response.latency_ms if response else None,
                cost_rmb=response.cost_rmb if response else None,
                provider_request_id=(
                    response.provider_request_id if response else provider_request_id
                ),
                pricing_snapshot_id=(
                    response.pricing_snapshot_id if response else None
                ),
                status=status,
                error_code=error_code,
                provider_error_code=provider_error_code,
            )
        )

    def _fail_run(self, run_id: str) -> None:
        if self.run_store.load_state(run_id) == RunState.BLIND_REVIEW_RUNNING:
            self.run_store.transition(run_id, RunState.FAILED)

    @staticmethod
    def _cost_rmb(response: GatewayResponse) -> float:
        return (
            response.input_tokens * INPUT_RMB_PER_MILLION
            + response.output_tokens * OUTPUT_RMB_PER_MILLION
        ) / 1_000_000
