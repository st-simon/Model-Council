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
    text,
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
    provider_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_model_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    uncached_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_creation_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_read_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_rmb: Mapped[float | None] = mapped_column(nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pricing_snapshot_id: Mapped[str | None] = mapped_column(String(200), nullable=True)


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
    provider_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_model_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    uncached_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_creation_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cache_read_input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_rmb: Mapped[float | None] = mapped_column(nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pricing_snapshot_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
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
            row.provider_request_id = response.provider_request_id
            row.pricing_snapshot_id = response.pricing_snapshot_id
            row.finished_at = datetime.now(UTC)
            session.commit()

    def finish_attempt_failure(
        self,
        attempt_id: int,
        error_code: str,
        status: AttemptStatus,
        *,
        provider_error_code: str | None = None,
        provider_request_id: str | None = None,
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
            row.provider_error_code = provider_error_code
            row.provider_request_id = provider_request_id
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
            row.provider_request_id = response.provider_request_id
            row.pricing_snapshot_id = response.pricing_snapshot_id
            session.commit()

    def save_failure(
        self,
        run_id: str,
        role: str,
        error_code: str,
        retryable: bool = False,
        max_attempts: int = 1,
        *,
        provider_error_code: str | None = None,
        provider_request_id: str | None = None,
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
            row.provider_error_code = provider_error_code
            row.provider_request_id = provider_request_id
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

    def reconcile_preprovider_failure(self, run_id: str, error_code: str) -> bool:
        """Atomically close one legacy attempt proven not to have reached a provider."""
        if error_code != "LOCAL_PROXY_PREFLIGHT_FAILED":
            raise ValueError("unsupported reconciliation error code")
        statement = text(
            "SELECT r.state AS run_state, c.call_id, c.status AS call_status, "
            "c.error_code AS call_error_code, c.provider AS call_provider, "
            "c.actual_model_id AS call_model, c.input_tokens AS call_input, "
            "c.output_tokens AS call_output, c.cost_rmb AS call_cost, "
            "c.provider_request_id AS call_request_id, c.output_json, "
            "a.attempt_id, a.status AS attempt_status, "
            "a.error_code AS attempt_error_code, a.provider AS attempt_provider, "
            "a.actual_model_id AS attempt_model, a.input_tokens AS attempt_input, "
            "a.output_tokens AS attempt_output, a.cost_rmb AS attempt_cost, "
            "a.provider_request_id AS attempt_request_id "
            "FROM runs r JOIN calls c ON c.run_id = r.run_id "
            "JOIN call_attempts a ON a.call_id = c.call_id "
            "WHERE r.run_id = :run_id"
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement, {"run_id": run_id}).mappings().all()
            if len(rows) != 1:
                raise ValueError("expected exactly one legacy call attempt")
            row = rows[0]
            evidence_fields = (
                "call_provider",
                "call_model",
                "call_input",
                "call_output",
                "call_cost",
                "call_request_id",
                "output_json",
                "attempt_provider",
                "attempt_model",
                "attempt_input",
                "attempt_output",
                "attempt_cost",
                "attempt_request_id",
            )
            if any(row[field] is not None for field in evidence_fields):
                raise ValueError("not an untouched pre-provider attempt")
            already_closed = (
                row["run_state"] == RunState.FAILED.value
                and row["call_status"] == CallStatus.FAILED_TERMINAL.value
                and row["attempt_status"] == AttemptStatus.FAILED_TERMINAL.value
                and row["call_error_code"] == error_code
                and row["attempt_error_code"] == error_code
            )
            if already_closed:
                return False
            if (
                row["run_state"] != RunState.BLIND_REVIEW_RUNNING.value
                or row["call_status"] != CallStatus.RUNNING.value
                or row["attempt_status"] != AttemptStatus.RUNNING.value
            ):
                raise ValueError("legacy attempt is not in the expected running state")
            finished_at = datetime.now(UTC).isoformat()
            connection.execute(
                text(
                    "UPDATE call_attempts SET status = :status, "
                    "error_code = :error_code, finished_at = :finished_at "
                    "WHERE attempt_id = :attempt_id"
                ),
                {
                    "status": AttemptStatus.FAILED_TERMINAL.value,
                    "error_code": error_code,
                    "finished_at": finished_at,
                    "attempt_id": row["attempt_id"],
                },
            )
            connection.execute(
                text(
                    "UPDATE calls SET status = :status, error_code = :error_code "
                    "WHERE call_id = :call_id"
                ),
                {
                    "status": CallStatus.FAILED_TERMINAL.value,
                    "error_code": error_code,
                    "call_id": row["call_id"],
                },
            )
            connection.execute(
                text("UPDATE runs SET state = :state WHERE run_id = :run_id"),
                {"state": RunState.FAILED.value, "run_id": run_id},
            )
            connection.execute(
                text(
                    "INSERT INTO run_transitions (run_id, from_state, to_state) "
                    "VALUES (:run_id, :from_state, :to_state)"
                ),
                {
                    "run_id": run_id,
                    "from_state": RunState.BLIND_REVIEW_RUNNING.value,
                    "to_state": RunState.FAILED.value,
                },
            )
            return True

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
            provider_error_code=row.provider_error_code,
            provider=row.provider,
            actual_model_id=row.actual_model_id,
            input_tokens=row.input_tokens,
            uncached_input_tokens=row.uncached_input_tokens,
            cache_creation_input_tokens=row.cache_creation_input_tokens,
            cache_read_input_tokens=row.cache_read_input_tokens,
            output_tokens=row.output_tokens,
            latency_ms=row.latency_ms,
            cost_rmb=row.cost_rmb,
            provider_request_id=row.provider_request_id,
            pricing_snapshot_id=row.pricing_snapshot_id,
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
            provider_error_code=row.provider_error_code,
            provider=row.provider,
            actual_model_id=row.actual_model_id,
            input_tokens=row.input_tokens,
            uncached_input_tokens=row.uncached_input_tokens,
            cache_creation_input_tokens=row.cache_creation_input_tokens,
            cache_read_input_tokens=row.cache_read_input_tokens,
            output_tokens=row.output_tokens,
            latency_ms=row.latency_ms,
            cost_rmb=row.cost_rmb,
            provider_request_id=row.provider_request_id,
            pricing_snapshot_id=row.pricing_snapshot_id,
            started_at=row.started_at,
            finished_at=row.finished_at,
            next_retry_at=row.next_retry_at,
        )
