"""Charts screen — spending over time and per-model bar chart using plotext."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, Static

import tokenmeter
from tokenmeter.tui.widgets.spark_chart import SparkChart


class ChartsScreen(Widget):
    """Displays ASCII charts for spending over the last 30 days and per-model breakdown."""

    def __init__(self, meter: tokenmeter.Meter) -> None:
        super().__init__()
        self._meter = meter

    def compose(self) -> ComposeResult:
        yield Label("Charts", classes="section-title")
        since = datetime.now() - timedelta(days=30)
        records = self._meter.tracker.get_records(since=since)

        if not records:
            yield Static("No usage data in the last 30 days.", classes="muted")
            return

        # Build daily spending series
        daily: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for r in records:
            day = r.timestamp.strftime("%m-%d")
            daily[day] += r.total_cost

        # Sort by date key
        sorted_days = sorted(daily.keys())
        daily_values = [float(daily[d]) for d in sorted_days]

        yield Label("Daily Spending — last 30 days", classes="section-title")
        yield SparkChart(
            title="Daily cost ($)",
            x_labels=sorted_days,
            values=daily_values,
            id="chart-spending",
        )

        # Build per-model cost breakdown
        model_costs: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for r in records:
            model_costs[r.model] += r.total_cost

        sorted_models = sorted(model_costs.keys(), key=lambda m: model_costs[m], reverse=True)
        model_values = [float(model_costs[m]) for m in sorted_models]

        yield Label("Cost by Model — last 30 days", classes="section-title")
        yield SparkChart(
            title="Cost ($)",
            x_labels=sorted_models,
            values=model_values,
            id="chart-models",
            bar=True,
        )
