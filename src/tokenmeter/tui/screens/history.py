"""History screen — scrollable DataTable of UsageRecords with filters."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Input, Label, Static, Widget

import tokenmeter


class HistoryScreen(Widget):
    """Displays a scrollable DataTable of recent usage records."""

    filter_model: reactive[str] = reactive("")
    filter_provider: reactive[str] = reactive("")

    def __init__(self, meter: tokenmeter.Meter) -> None:
        super().__init__()
        self._meter = meter

    def compose(self) -> ComposeResult:
        yield Label("Usage History", classes="section-title")
        yield Static("Filter:", id="filter-label")
        yield Input(placeholder="Filter by model…", id="filter-model")
        yield Input(placeholder="Filter by provider…", id="filter-provider")
        yield DataTable(id="history-table", cursor_type="row")

    def on_mount(self) -> None:
        self._populate_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-model":
            self.filter_model = event.value
        elif event.input.id == "filter-provider":
            self.filter_provider = event.value
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear(columns=True)

        table.add_columns(
            "Timestamp",
            "Model",
            "Provider",
            "In (tok)",
            "Out (tok)",
            "Cost ($)",
            "Water (mL)",
            "Energy (Wh)",
        )

        model_filter = self.filter_model.strip().lower() or None
        provider_filter = self.filter_provider.strip().lower() or None

        records = self._meter.tracker.get_records()
        records = sorted(records, key=lambda r: r.timestamp, reverse=True)

        for r in records:
            if model_filter and model_filter not in r.model.lower():
                continue
            if provider_filter and provider_filter not in r.provider.lower():
                continue

            table.add_row(
                r.timestamp.strftime("%Y-%m-%d %H:%M"),
                r.model,
                r.provider,
                f"{r.input_tokens:,}",
                f"{r.output_tokens:,}",
                f"{r.total_cost:.6f}",
                f"{r.water_ml:.1f}" if r.water_ml > 0 else "—",
                f"{r.energy_wh:.4f}" if r.energy_wh > 0 else "—",
            )
