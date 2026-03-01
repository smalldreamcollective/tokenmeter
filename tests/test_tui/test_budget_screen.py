"""Tests for the Budget screen."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")

from textual.widgets import Static  # noqa: E402

import tokenmeter  # noqa: E402
from tokenmeter.tui.app import TokenmeterApp  # noqa: E402
from tokenmeter.tui.screens.budget import BudgetScreen  # noqa: E402


@pytest.mark.asyncio
async def test_budget_screen_shows_empty_message_when_no_budgets(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no budgets are configured, a helpful message should be shown."""
    monkeypatch.setattr("tokenmeter.tui.screens.budget.load_budgets", lambda: [])
    meter = tokenmeter.Meter(storage="memory")
    screen = BudgetScreen(meter)
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await app.mount(screen)
        empty = screen.query_one("#budget-empty", Static)
        assert empty is not None
        assert "No budgets" in str(empty.renderable)


@pytest.mark.asyncio
async def test_budget_screen_composes_without_crash() -> None:
    """Budget screen should compose without raising even with no storage data."""
    meter = tokenmeter.Meter(storage="memory")
    screen = BudgetScreen(meter)
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await app.mount(screen)
        # Composed without error
