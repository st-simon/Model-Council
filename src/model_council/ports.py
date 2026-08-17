from __future__ import annotations

from pathlib import Path
from typing import Protocol

from model_council.models import (
    CallLogEvent,
    GatewayRequest,
    GatewayResponse,
    ReviewInput,
    ReviewOutput,
    RunState,
    StoredCall,
)


class ModelGateway(Protocol):
    async def review(self, request: GatewayRequest) -> GatewayResponse: ...

    async def repair(
        self, request: GatewayRequest, raw_output: str, validation_error: str
    ) -> GatewayResponse: ...


class RunStore(Protocol):
    def create_or_load(self, request: ReviewInput) -> RunState: ...

    def transition(self, run_id: str, state: RunState) -> None: ...

    def claim_call(
        self,
        run_id: str,
        role: str,
        context_hash: str,
        prompt_hash: str,
    ) -> StoredCall | None: ...

    def save_success(
        self, run_id: str, role: str, response: GatewayResponse, output: ReviewOutput
    ) -> None: ...

    def save_failure(self, run_id: str, role: str, error_code: str) -> None: ...

    def save_invalid(self, run_id: str, role: str, error_code: str) -> None: ...

    def list_calls(self, run_id: str) -> list[StoredCall]: ...

    def load_request(self, run_id: str) -> ReviewInput: ...

    def load_state(self, run_id: str) -> RunState: ...


class ArtifactStore(Protocol):
    def write_call_input(self, request: GatewayRequest) -> None: ...

    def write_raw_output(
        self,
        project_id: str,
        run_id: str,
        role: str,
        attempt: int,
        raw_output: str,
    ) -> None: ...

    def write_call_log(self, event: CallLogEvent) -> None: ...

    def write_report(
        self, request: ReviewInput, state: RunState, calls: list[StoredCall]
    ) -> Path: ...
