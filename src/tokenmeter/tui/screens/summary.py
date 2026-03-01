"""Summary screen — aggregated totals by model/provider."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import DataTable, Label, Select, Static, Widget

import tokenmeter


_GROUP_BY_OPTIONS: list[tuple[str, str]] = [
    ("Model", "model"),
    ("Provider", "provider"),
    ("User ID", "user_id"),
    ("Session ID", "session_id"),
]


class SummaryScreen(Widget):
    """Displays aggregated usage metrics grouped by a chosen dimension."""

    def __init__(self, meter: tokenmeter.Meter) -> None:
        super().__init__()
        self._meter = meter
        self._group_by = "model"

    def compose(self) -> ComposeResult:
        yield Label("Usage Summary", classes="section-title")
        yield Select(
            [(label, value) for label, value in _GROUP_BY_OPTIONS],
            value="model",
            id="group-by-select",
        )
        yield DataTable(id="summary-table", cursor_type="row")
        yield Static(id="summary-totals")

    def on_mount(self) -> None:
        self._populate_table()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._group_by = str(event.value)
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.query_one("#summary-table", DataTable)
        table.clear(columns=True)

        table.add_columns(
            "Group",
            "Calls",
            "Input (tok)",
            "Output (tok)",
            "Cost ($)",
            "Water (mL)",
            "Energy (Wh)",
        )

        summary = self._meter.tracker.get_summary_detailed(group_by=self._group_by)
        rows = sorted(summary.items(), key=lambda kv: kv[1].total_cost, reverse=True)

        total_cost = sum(r.total_cost for r in summary.values())
        total_calls = sum(r.call_count for r in summary.values())
        total_input = sum(r.total_input_tokens for r in summary.values())
        total_output = sum(r.total_output_tokens for r in summary.values())
        total_water = sum(r.total_water_ml for r in summary.values())
        total_energy = sum(r.total_energy_wh for r in summary.values())

        for group_key, row in rows:
            table.add_row(
                group_key,
                str(row.call_count),
                f"{row.total_input_tokens:,}",
                f"{row.total_output_tokens:,}",
                f"{row.total_cost:.6f}",
                f"{row.total_water_ml:.1f}" if row.total_water_ml > 0 else "—",
                f"{row.total_energy_wh:.4f}" if row.total_energy_wh > 0 else "—",
            )

        totals_widget = self.query_one("#summary-totals", Static)
        water_str = f" | Water: {total_water:.1f} mL" if total_water > 0 else ""
        energy_str = f" | Energy: {total_energy:.4f} Wh" if total_energy > 0 else ""
        totals_widget.update(
            f"Totals — Calls: {total_calls} | "
            f"Tokens: {total_input + total_output:,} ({total_input:,} in / {total_output:,} out) | "
            f"Cost: ${total_cost:.6f}{water_str}{energy_str}"
        )
