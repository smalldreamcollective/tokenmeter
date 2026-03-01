from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from tokenmeter._types import BudgetConfig, BudgetExceededError, BudgetStatus
from tokenmeter.tracker import UsageTracker


class BudgetManager:
    """Manages spending limits and enforcement."""

    def __init__(self, tracker: UsageTracker) -> None:
        self._tracker = tracker
        self._budgets: list[BudgetConfig] = []

    def set_budget(
        self,
        limit: float | Decimal,
        period: str = "total",
        scope: str = "global",
        action: str = "warn",
    ) -> BudgetConfig:
        """Set a spending limit.

        Args:
            limit: Maximum spending in USD.
            period: "session", "daily", "weekly", "monthly", or "total".
            scope: "global" or a specific user_id/session_id.
            action: "warn" (log warning) or "block" (raise BudgetExceededError).
        """
        config = BudgetConfig(
            limit=Decimal(str(limit)),
            period=period,
            scope=scope,
            action=action,
        )
        self._budgets.append(config)
        return config

    def check(self, user_id: str | None = None) -> list[BudgetStatus]:
        """Check all budgets and return their current status."""
        return [self._check_one(b, user_id) for b in self._budgets]

    def would_exceed(
        self,
        estimated_cost: Decimal | float,
        user_id: str | None = None,
    ) -> bool:
        """Check if a pending request would push past any budget."""
        cost = Decimal(str(estimated_cost))
        for budget in self._budgets:
            status = self._check_one(budget, user_id)
            if status.spent + cost > budget.limit:
                return True
        return False

    def enforce(
        self,
        estimated_cost: Decimal | float,
        user_id: str | None = None,
    ) -> None:
        """Raise BudgetExceededError if any budget with action='block' would be exceeded."""
        cost = Decimal(str(estimated_cost))
        for budget in self._budgets:
            if budget.action != "block":
                continue
            status = self._check_one(budget, user_id)
            if status.spent + cost > budget.limit:
                raise BudgetExceededError(status)

    def remove_budget(self, budget: BudgetConfig) -> None:
        """Remove a previously set budget."""
        self._budgets.remove(budget)

    def list_budgets(self) -> list[BudgetConfig]:
        """Return all configured budgets."""
        return list(self._budgets)

    def _check_one(self, config: BudgetConfig, user_id: str | None = None) -> BudgetStatus:
        since = _period_start(config.period)
        kwargs: dict[str, Any] = {}
        if since is not None:
            kwargs["since"] = since
        if config.scope != "global":
            if config.scope.startswith("user:"):
                kwargs["user_id"] = config.scope[5:]
            elif config.scope.startswith("session:"):
                kwargs["session_id"] = config.scope[8:]
        elif user_id is not None:
            kwargs["user_id"] = user_id

        spent = self._tracker.get_total(**kwargs)
        remaining = max(Decimal("0"), config.limit - spent)
        utilization = float(spent / config.limit) if config.limit > 0 else 0.0

        return BudgetStatus(
            config=config,
            spent=spent,
            remaining=remaining,
            utilization=utilization,
            is_exceeded=spent >= config.limit,
        )


def _period_start(period: str) -> datetime | None:
    """Calculate the start of the current period."""
    now = datetime.now()
    if period == "total":
        return None
    if period == "session":
        return None  # Session filtering is done by session_id, not time
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "weekly":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unknown period: {period!r}. Use 'session', 'daily', 'weekly', 'monthly', or 'total'.")
