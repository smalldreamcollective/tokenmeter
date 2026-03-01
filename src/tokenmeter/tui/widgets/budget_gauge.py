"""BudgetGauge — reusable widget showing a single budget as a labelled progress bar."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Label, ProgressBar, Static, Widget

from tokenmeter._types import BudgetStatus


class BudgetGauge(Widget):
    """Displays a single budget's utilization as a progress bar with labels."""

    DEFAULT_CSS = """
    BudgetGauge {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid $surface-lighten-2;
    }
    """

    def __init__(self, status: BudgetStatus) -> None:
        super().__init__()
        self._status = status

    def compose(self) -> ComposeResult:
        cfg = self._status.config
        pct = min(self._status.utilization, 1.0)
        color_class = "ok" if pct < 0.8 else ("warning" if pct < 1.0 else "exceeded")

        yield Label(
            f"{cfg.period.title()} — {cfg.scope}  [{cfg.action}]",
            classes="gauge-label",
        )
        yield ProgressBar(
            total=100,
            show_eta=False,
            show_percentage=True,
        )
        yield Static(
            f"Spent: ${self._status.spent:.4f} / ${cfg.limit:.2f}  "
            f"Remaining: ${self._status.remaining:.4f}  "
            f"({int(pct * 100)}%)",
            classes=f"gauge-detail {color_class}",
        )

    def on_mount(self) -> None:
        bar = self.query_one(ProgressBar)
        bar.advance(int(min(self._status.utilization, 1.0) * 100))
