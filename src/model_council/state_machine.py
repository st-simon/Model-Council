from __future__ import annotations

from model_council.models import InvalidStateTransition, RunState

ALLOWED_TRANSITIONS: dict[RunState, set[RunState]] = {
    RunState.INITIALIZED: {RunState.BLIND_REVIEW_RUNNING},
    RunState.BLIND_REVIEW_RUNNING: {
        RunState.BLIND_REVIEW_DONE,
        RunState.FAILED,
    },
    RunState.BLIND_REVIEW_DONE: {RunState.COMPLETED},
    RunState.COMPLETED: set(),
    RunState.FAILED: set(),
}


def ensure_transition(current: RunState, target: RunState) -> None:
    if current == target:
        return
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(f"{current.value} -> {target.value}")
