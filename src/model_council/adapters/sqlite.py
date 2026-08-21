from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from model_council.models import (
    AttemptKind,
    AttemptStatus,
    CallStatus,
    GatewayResponse,
    ReviewInput,
    ReviewOutput,
    RunState,
    StoredAttempt,
    StoredCall,
)
from model_council.state_machine import ensure_transition


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[str] = mapped_column(String(50))
    request_json: Mapped[str] = mapped_column(Text)
    reserved_cost_rmb: Mapped[float] = mapped_column(default=0.0)


class CallRow(Base):
    __tablename__ = "calls"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "role",
            "model_alias",
            "context_hash",
            "prompt_hash",
            name="uq_logical_call",
        ),
    )

    call_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"))
    role: Mapped[str] = mapped_column(String(100))
    model_alias: Mapped[str] = mapped_column(String(100))
    context_hash: Mapped[str] = mapped_column(String(64))
    prompt_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_model_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    uncached_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_creation_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_read_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_rmb: Mapped[float | None] = mapped_column(nullable=True)


class CallAttemptRow(Base):
    __tablename__ = "call_attempts"
    __table_args__ = (
        UniqueConstraint("call_id", "ordinal", name="uq_call_attempt_ordinal"),
    )

    attempt_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.call_id"))
    ordinal: Mapped[int]
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_model_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    uncached_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_creation_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_read_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_rmb: Mapped[float | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TransitionRow(Base):
    __tablename__ = "run_transitions"

    transition_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"))
    from_state: Mapped[str] = mapped_column(String(50))
    to_state: Mapped[str] = mapped_column(String(50))


class SQLiteRunStore:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(self.engine)

    def create_or_load(self, request: ReviewInput) -> RunState:
        with Session(self.engine) as session:
            row = session.get(RunRow, request.run_id)
            if row is None:
                row = RunRow(
                    run_id=request.run_id,
                    state=RunState.INITIALIZED.value,
                    request_json=request.model_dump_json(),
                )
                session.add(row)
                session.commit()
            return RunState(row.state)

    def transition(self, run_id: str, state: RunState) -> None:
        with Session(self.engine) as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(run_id)
            current = RunState(row.state)
            ensure_transition(current, state)
            if current == state:
                return
            row.state = state.value
            session.add(
                TransitionRow(
                    run_id=run_id,
                    from_state=current.value,
                    to_state=state.value,
                )
            )
            session.commit()

    def list_transitions(self, run_id: str) -> list[tuple[RunState, RunState]]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(TransitionRow)
                .where(TransitionRow.run_id == run_id)
                .order_by(TransitionRow.transition_id)
            ).all()
            return [(RunState(row.from_state), RunState(row.to_state)) for row in rows]

    def claim_call(
        self,
        run_id: str,
        role: str,
        model_alias: str,
        context_hash: str,
        prompt_hash: str,
    ) -> StoredCall | None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(CallRow).where(
                    CallRow.run_id == run_id,
                    CallRow.role == role,
                    CallRow.model_alias == model_alias,
                    CallRow.context_hash == context_hash,
                    CallRow.prompt_hash == prompt_hash,
                )
            )
            if row is not None and row.status in {
                CallStatus.SUCCEEDED.value,
                CallStatus.FAILED.value,
                CallStatus.FAILED_TERMINAL.value,
                CallStatus.INVALID.value,
            }:
                return self._stored_call(row)
            if row is None:
                session.add(
                    CallRow(
                        run_id=run_id,
                        role=role,
                        model_alias=model_alias,
                        context_hash=context_hash,
                        prompt_hash=prompt_hash,
                        status=CallStatus.RUNNING.value,
                    )
                )
                session.commit()
            return None

    def start_attempt(self, run_id: str, role: str, kind: AttemptKind) -> StoredAttempt:
        with Session(self.engine) as session:
            call = session.scalar(
                select(CallRow).where(CallRow.run_id == run_id, CallRow.role == role)
            )
            if call is None:
                raise KeyError((run_id, role))
            now = datetime.now(UTC)
            attempts = session.scalars(
                select(CallAttemptRow)
                .where(CallAttemptRow.call_id == call.call_id)
                .order_by(CallAttemptRow.ordinal)
            ).all()
            for previous in attempts:
                if previous.status == AttemptStatus.RUNNING.value:
                    previous.status = AttemptStatus.TIMED_OUT.value
                    previous.finished_at = now
            row = CallAttemptRow(
                call_id=call.call_id,
                ordinal=len(attempts) + 1,
                kind=kind.value,
                status=AttemptStatus.RUNNING.value,
                started_at=now,
            )
            session.add(row)
            session.flush()
            stored = self._stored_attempt(row, role)
            session.commit()
            return stored

    def finish_attempt_success(
        self, attempt_id: int, response: GatewayResponse
    ) -> None:
        with Session(self.engine) as session:
            row = session.get(CallAttemptRow, attempt_id)
            if row is None:
                raise KeyError(attempt_id)
            row.status = AttemptStatus.SUCCEEDED.value
            row.provider = response.provider
            row.actual_model_id = response.actual_model_id
            row.input_tokens = response.input_tokens
            row.uncached_input_tokens = response.uncached_input_tokens
            row.cache_creation_input_tokens = response.cache_creation_input_tokens
            row.cache_read_input_tokens = response.cache_read_input_tokens
            row.output_tokens = response.output_tokens
            row.latency_ms = response.latency_ms
            row.cost_rmb = response.cost_rmb
            row.finished_at = datetime.now(UTC)
            session.commit()

    def finish_attempt_failure(
        self,
        attempt_id: int,
        error_code: str,
        status: AttemptStatus,
    ) -> None:
        if status not in {
            AttemptStatus.RETRY_WAIT,
            AttemptStatus.TIMED_OUT,
            AttemptStatus.INVALID,
            AttemptStatus.FAILED_TERMINAL,
        }:
            raise ValueError(f"invalid failure status: {status.value}")
        with Session(self.engine) as session:
            row = session.get(CallAttemptRow, attempt_id)
            if row is None:
                raise KeyError(attempt_id)
            row.status = status.value
            row.error_code = error_code
            row.finished_at = datetime.now(UTC)
            row.next_retry_at = (
                datetime.now(UTC) if status == AttemptStatus.RETRY_WAIT else None
            )
            session.commit()

    def save_success(
        self, run_id: str, role: str, response: GatewayResponse, output: ReviewOutput
    ) -> None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(CallRow).where(CallRow.run_id == run_id, CallRow.role == role)
            )
            if row is None:
                raise KeyError((run_id, role))
            row.status = CallStatus.SUCCEEDED.value
            row.output_json = output.model_dump_json()
            row.provider = response.provider
            row.actual_model_id = response.actual_model_id
            row.input_tokens = response.input_tokens
            row.uncached_input_tokens = response.uncached_input_tokens
            row.cache_creation_input_tokens = response.cache_creation_input_tokens
            row.cache_read_input_tokens = response.cache_read_input_tokens
            row.output_tokens = response.output_tokens
            row.latency_ms = response.latency_ms
            row.cost_rmb = response.cost_rmb
            session.commit()

    def save_failure(
        self,
        run_id: str,
        role: str,
        error_code: str,
        retryable: bool = False,
        max_attempts: int = 1,
    ) -> None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(CallRow).where(CallRow.run_id == run_id, CallRow.role == role)
            )
            if row is None:
                raise KeyError((run_id, role))
            attempts = session.scalars(
                select(CallAttemptRow).where(
                    CallAttemptRow.call_id == row.call_id,
                    CallAttemptRow.kind == AttemptKind.REVIEW.value,
                )
            ).all()
            row.status = (
                CallStatus.RETRY_WAIT.value
                if retryable and len(attempts) < max_attempts
                else CallStatus.FAILED_TERMINAL.value
            )
            row.error_code = error_code
            session.commit()

    def save_invalid(self, run_id: str, role: str, error_code: str) -> None:
        self._save_terminal_failure(run_id, role, error_code, CallStatus.INVALID)

    def _save_terminal_failure(
        self, run_id: str, role: str, error_code: str, status: CallStatus
    ) -> None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(CallRow).where(CallRow.run_id == run_id, CallRow.role == role)
            )
            if row is None:
                raise KeyError((run_id, role))
            row.status = status.value
            row.error_code = error_code
            session.commit()

    def list_calls(self, run_id: str) -> list[StoredCall]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(CallRow).where(CallRow.run_id == run_id).order_by(CallRow.role)
            ).all()
            return [self._stored_call(row) for row in rows]

    def total_cost_rmb(self, run_id: str) -> float:
        return sum(call.cost_rmb or 0.0 for call in self.list_calls(run_id))

    def reserve_budget(
        self,
        run_id: str,
        estimated_cost_rmb: float,
        hard_limit_rmb: float | None,
    ) -> bool:
        with Session(self.engine) as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(run_id)
            projected = row.reserved_cost_rmb + estimated_cost_rmb
            if hard_limit_rmb is not None and projected > hard_limit_rmb:
                return False
            row.reserved_cost_rmb = projected
            session.commit()
            return True

    def list_attempts(self, run_id: str) -> list[StoredAttempt]:
        with Session(self.engine) as session:
            rows = session.execute(
                select(CallAttemptRow, CallRow.role)
                .join(CallRow, CallAttemptRow.call_id == CallRow.call_id)
                .where(CallRow.run_id == run_id)
                .order_by(CallAttemptRow.attempt_id)
            ).all()
            return [self._stored_attempt(row, role) for row, role in rows]

    def load_request(self, run_id: str) -> ReviewInput:
        with Session(self.engine) as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(run_id)
            return ReviewInput.model_validate_json(row.request_json)

    def load_state(self, run_id: str) -> RunState:
        with Session(self.engine) as session:
            row = session.get(RunRow, run_id)
            if row is None:
                raise KeyError(run_id)
            return RunState(row.state)

    @staticmethod
    def _stored_call(row: CallRow) -> StoredCall:
        output = (
            ReviewOutput.model_validate_json(row.output_json)
            if row.output_json is not None
            else None
        )
        return StoredCall(
            role=row.role,
            model_alias=row.model_alias,
            status=CallStatus(row.status),
            prompt_hash=row.prompt_hash,
            context_hash=row.context_hash,
            output=output,
            error_code=row.error_code,
            provider=row.provider,
            actual_model_id=row.actual_model_id,
            input_tokens=row.input_tokens,
            uncached_input_tokens=row.uncached_input_tokens,
            cache_creation_input_tokens=row.cache_creation_input_tokens,
            cache_read_input_tokens=row.cache_read_input_tokens,
            output_tokens=row.output_tokens,
            latency_ms=row.latency_ms,
            cost_rmb=row.cost_rmb,
        )

    @staticmethod
    def _stored_attempt(row: CallAttemptRow, role: str) -> StoredAttempt:
        return StoredAttempt(
            attempt_id=row.attempt_id,
            role=role,
            ordinal=row.ordinal,
            kind=AttemptKind(row.kind),
            status=AttemptStatus(row.status),
            error_code=row.error_code,
            provider=row.provider,
            actual_model_id=row.actual_model_id,
            input_tokens=row.input_tokens,
            uncached_input_tokens=row.uncached_input_tokens,
            cache_creation_input_tokens=row.cache_creation_input_tokens,
            cache_read_input_tokens=row.cache_read_input_tokens,
            output_tokens=row.output_tokens,
            latency_ms=row.latency_ms,
            cost_rmb=row.cost_rmb,
            started_at=row.started_at,
            finished_at=row.finished_at,
            next_retry_at=row.next_retry_at,
        )
