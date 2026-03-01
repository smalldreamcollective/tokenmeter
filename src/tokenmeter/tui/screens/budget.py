"""Budget screen — ProgressBar per budget with utilization info."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Label, Static, Widget

import tokenmeter
from tokenmeter.config import load_budgets
from tokenmeter.tui.widgets.budget_gauge import BudgetGauge


class BudgetScreen(Widget):
    """Displays current budget utilization with progress bars."""

    def __init__(self, meter: tokenmeter.Meter) -> None:
        super().__init__()
        self._meter = meter

    def compose(self) -> ComposeResult:
        yield Label("Budget Status", classes="section-title")

        # Load saved budgets and register them on a fresh meter
        saved = load_budgets()
        if not saved:
            yield Static(
                "No budgets configured.\n\n"
                "Run: tokenmeter budget set <amount> --period daily",
                id="budget-empty",
            )
            return

        # Ensure budgets are loaded into the meter
        for cfg in saved:
            self._meter.budget.set_budget(
                limit=cfg.limit,
                period=cfg.period,
                scope=cfg.scope,
                action=cfg.action,
            )

        statuses = self._meter.budget.check()
        if not statuses:
            yield Static("No budget data available.", id="budget-empty")
            return

        yield Static("", id="budget-container")
        for status in statuses:
            yield BudgetGauge(status)
