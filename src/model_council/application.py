from __future__ import annotations

import asyncio

from pydantic import ValidationError

from model_council.budget import BudgetGuard, HardBudgetExceeded
from model_council.models import (
    AttemptKind,
    AttemptStatus,
    CallLogEvent,
    CallStatus,
    GatewayRequest,
    GatewayResponse,
    ModelCallError,
    PromptEnvelope,
    ReviewInput,
    ReviewOutput,
    RunState,
    RunSummary,
)
from model_council.ports import ArtifactStore, ModelGateway, RunStore
from model_council.prompting import PromptBuilder


class CouncilApplication:
    def __init__(
        self,
        gateway: ModelGateway,
        run_store: RunStore,
        artifact_store: ArtifactStore,
        budget_guard: BudgetGuard | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.gateway = gateway
        self.run_store = run_store
        self.artifact_store = artifact_store
        self.budget_guard = budget_guard or BudgetGuard()
        self.prompt_builder = prompt_builder or PromptBuilder()

    async def start_review(self, request: ReviewInput) -> RunSummary:
        state = self.run_store.create_or_load(request)
        if state == RunState.COMPLETED:
            return self._summary(request, state)

        self.run_store.transition(request.run_id, RunState.BLIND_REVIEW_RUNNING)
        gateway_requests = [
            self.prompt_builder.build(request, role) for role in request.reviewers
        ]
        await asyncio.gather(*(self._run_call(item) for item in gateway_requests))

        calls = self.run_store.list_calls(request.run_id)
        succeeded = [call for call in calls if call.status.value == "SUCCEEDED"]
        if len(succeeded) >= request.minimum_successful_reviewers:
            self.run_store.transition(request.run_id, RunState.BLIND_REVIEW_DONE)
            state = RunState.COMPLETED
        elif any(call.status == CallStatus.RETRY_WAIT for call in calls):
            state = RunState.BLIND_REVIEW_RUNNING
        else:
            state = RunState.FAILED
        if state != RunState.BLIND_REVIEW_RUNNING:
            self.run_store.transition(request.run_id, state)
        return self._summary(request, state)

    async def resume(self, run_id: str) -> RunSummary:
        return await self.start_review(self.run_store.load_request(run_id))

    def status(self, run_id: str) -> RunSummary:
        request = self.run_store.load_request(run_id)
        return self._summary(request, self.run_store.load_state(run_id))

    async def _run_call(self, request: GatewayRequest) -> None:
        context_hash = (
            request.envelope.context_hash
            if request.envelope is not None
            else self._hash(request.context)
        )
        prompt_hash = (
            request.envelope.envelope_hash
            if request.envelope is not None
            else self._hash(request.prompt)
        )
        existing = self.run_store.claim_call(
            request.run_id,
            request.role,
            request.model_alias or request.role,
            context_hash,
            prompt_hash,
        )
        if existing is not None:
            return
        self.artifact_store.write_call_input(request)
        review_input = self.run_store.load_request(request.run_id)
        try:
            self.budget_guard.check(
                review_input.budget,
                spent_rmb=self.run_store.total_cost_rmb(request.run_id),
                required=True,
            )
            if not self.run_store.reserve_budget(
                request.run_id,
                review_input.budget.estimated_call_cost_rmb,
                review_input.budget.hard_limit_rmb,
            ):
                raise HardBudgetExceeded("BUDGET_HARD_LIMIT")
        except HardBudgetExceeded:
            self.run_store.save_failure(
                request.run_id,
                request.role,
                "BUDGET_HARD_LIMIT",
                retryable=False,
                max_attempts=review_input.max_provider_attempts,
            )
            self.artifact_store.write_call_log(
                CallLogEvent(
                    run_id=request.run_id,
                    role=request.role,
                    model_alias=request.model_alias or request.role,
                    prompt_hash=prompt_hash,
                    context_hash=context_hash,
                    status=CallStatus.FAILED_TERMINAL,
                    error_code="BUDGET_HARD_LIMIT",
                )
            )
            return
        attempt = self.run_store.start_attempt(
            request.run_id, request.role, AttemptKind.REVIEW
        )
        try:
            response = await self.gateway.review(request)
        except ModelCallError as error:
            self._record_model_failure(
                request,
                review_input,
                attempt.attempt_id,
                error,
                prompt_hash,
                context_hash,
            )
            return
        self.run_store.finish_attempt_success(attempt.attempt_id, response)
        self.artifact_store.write_raw_output(
            request.project_id,
            request.run_id,
            request.role,
            0,
            response.raw_output,
        )
        output: ReviewOutput | None = None
        for repair_attempt in range(review_input.max_schema_repairs + 1):
            try:
                output = ReviewOutput.model_validate_json(response.raw_output)
                break
            except ValidationError as error:
                if repair_attempt == review_input.max_schema_repairs:
                    self.run_store.save_invalid(
                        request.run_id, request.role, "REVIEW_INVALID"
                    )
                    self._write_call_log(
                        request,
                        response,
                        prompt_hash,
                        context_hash,
                        CallStatus.INVALID,
                        "REVIEW_INVALID",
                    )
                    return
                repair = self.run_store.start_attempt(
                    request.run_id, request.role, AttemptKind.REPAIR
                )
                try:
                    response = await self.gateway.repair(
                        request, response.raw_output, str(error)
                    )
                except ModelCallError as repair_error:
                    self._record_model_failure(
                        request,
                        review_input,
                        repair.attempt_id,
                        repair_error,
                        prompt_hash,
                        context_hash,
                    )
                    return
                self.run_store.finish_attempt_success(repair.attempt_id, response)
                self.artifact_store.write_raw_output(
                    request.project_id,
                    request.run_id,
                    request.role,
                    repair_attempt + 1,
                    response.raw_output,
                )
        if output is None:
            raise AssertionError("validated review output was not produced")
        self.run_store.save_success(request.run_id, request.role, response, output)
        self._write_call_log(
            request,
            response,
            prompt_hash,
            context_hash,
            CallStatus.SUCCEEDED,
        )

    def _record_model_failure(
        self,
        request: GatewayRequest,
        review_input: ReviewInput,
        attempt_id: int,
        error: ModelCallError,
        prompt_hash: str,
        context_hash: str,
    ) -> None:
        review_attempts = sum(
            attempt.role == request.role and attempt.kind == AttemptKind.REVIEW
            for attempt in self.run_store.list_attempts(request.run_id)
        )
        will_retry = error.retryable and (
            review_attempts < review_input.max_provider_attempts
        )
        failure_status = (
            CallStatus.RETRY_WAIT if will_retry else CallStatus.FAILED_TERMINAL
        )
        self.run_store.finish_attempt_failure(
            attempt_id,
            error.code,
            AttemptStatus.RETRY_WAIT if will_retry else AttemptStatus.FAILED_TERMINAL,
        )
        self.run_store.save_failure(
            request.run_id,
            request.role,
            error.code,
            retryable=error.retryable,
            max_attempts=review_input.max_provider_attempts,
        )
        self.artifact_store.write_call_log(
            CallLogEvent(
                run_id=request.run_id,
                role=request.role,
                model_alias=request.model_alias or request.role,
                prompt_hash=prompt_hash,
                context_hash=context_hash,
                status=failure_status,
                error_code=error.code,
            )
        )

    def _write_call_log(
        self,
        request: GatewayRequest,
        response: GatewayResponse,
        prompt_hash: str,
        context_hash: str,
        status: CallStatus,
        error_code: str | None = None,
    ) -> None:
        self.artifact_store.write_call_log(
            CallLogEvent(
                run_id=request.run_id,
                role=request.role,
                model_alias=request.model_alias or request.role,
                actual_model_id=response.actual_model_id,
                provider=response.provider,
                prompt_hash=prompt_hash,
                context_hash=context_hash,
                input_tokens=response.input_tokens,
                uncached_input_tokens=response.uncached_input_tokens,
                cache_creation_input_tokens=response.cache_creation_input_tokens,
                cache_read_input_tokens=response.cache_read_input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                cost_rmb=response.cost_rmb,
                provider_request_id=response.provider_request_id,
                pricing_snapshot_id=response.pricing_snapshot_id,
                status=status,
                error_code=error_code,
            )
        )

    def _summary(self, request: ReviewInput, state: RunState) -> RunSummary:
        calls = self.run_store.list_calls(request.run_id)
        report_path = self.artifact_store.write_report(request, state, calls)
        successful = [call.role for call in calls if call.status.value == "SUCCEEDED"]
        failed = [call.role for call in calls if call.status.value != "SUCCEEDED"]
        return RunSummary(
            run_id=request.run_id,
            state=state,
            successful_reviewers=successful,
            failed_reviewers=failed,
            partial_review=bool(successful and failed),
            report_path=report_path,
        )

    @staticmethod
    def _hash(value: object) -> str:
        return PromptEnvelope._hash(value)
