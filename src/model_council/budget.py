from __future__ import annotations

from enum import StrEnum

from model_council.models import BudgetPolicy


class BudgetDisposition(StrEnum):
    ALLOW = "ALLOW"
    SOFT_STOP = "SOFT_STOP"


class HardBudgetExceeded(RuntimeError):
    pass


class BudgetGuard:
    def check(
        self,
        policy: BudgetPolicy,
        spent_rmb: float,
        required: bool,
    ) -> BudgetDisposition:
        projected = spent_rmb + policy.estimated_call_cost_rmb
        if policy.hard_limit_rmb is not None and projected > policy.hard_limit_rmb:
            raise HardBudgetExceeded("BUDGET_HARD_LIMIT")
        if (
            not required
            and policy.soft_limit_rmb is not None
            and projected > policy.soft_limit_rmb
        ):
            return BudgetDisposition.SOFT_STOP
        return BudgetDisposition.ALLOW
