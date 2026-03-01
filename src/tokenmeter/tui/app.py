"""Root Textual application for the tokenmeter TUI dashboard."""

from __future__ import annotations

import os

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

import tokenmeter
from tokenmeter.tui.screens.advisor import AdvisorScreen
from tokenmeter.tui.screens.budget import BudgetScreen
from tokenmeter.tui.screens.charts import ChartsScreen
from tokenmeter.tui.screens.history import HistoryScreen
from tokenmeter.tui.screens.summary import SummaryScreen


class TokenmeterApp(App[None]):
    """Interactive terminal dashboard for tokenmeter usage data."""

    CSS_PATH = os.path.join(os.path.dirname(__file__), "tokenmeter.tcss")

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help_keys", "Keys", show=False),
    ]

    TITLE = "tokenmeter"
    SUB_TITLE = "AI Usage Dashboard"

    def __init__(self, db_path: str = "~/.tokenmeter/usage.db") -> None:
        super().__init__()
        self._db_path = db_path
        self._meter = tokenmeter.Meter(storage="sqlite", db_path=db_path)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="history"):
            with TabPane("History", id="history"):
                yield HistoryScreen(self._meter)
            with TabPane("Summary", id="summary"):
                yield SummaryScreen(self._meter)
            with TabPane("Budgets", id="budgets"):
                yield BudgetScreen(self._meter)
            with TabPane("Charts", id="charts"):
                yield ChartsScreen(self._meter)
            with TabPane("Advisor", id="advisor"):
                yield AdvisorScreen(self._meter)
        yield Footer()

    def action_refresh(self) -> None:
        """Refresh all data from storage."""
        self._meter = tokenmeter.Meter(storage="sqlite", db_path=self._db_path)
        self.notify("Data refreshed", timeout=2)
        self.refresh(layout=True)

    def action_help_keys(self) -> None:
        self.notify(
            "r=refresh  q=quit  tab=switch tab  arrow keys=navigate",
            title="Keyboard shortcuts",
            timeout=5,
        )
