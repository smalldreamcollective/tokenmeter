"""Tests for the History screen."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")

from textual.widgets import DataTable  # noqa: E402

import tokenmeter  # noqa: E402
from tokenmeter.tui.app import TokenmeterApp  # noqa: E402
from tokenmeter.tui.screens.history import HistoryScreen  # noqa: E402


def _make_meter_with_records() -> tokenmeter.Meter:
    meter = tokenmeter.Meter(storage="memory")
    meter.tracker.record_manual(
        model="claude-sonnet-4-5",
        input_tokens=100,
        output_tokens=50,
        provider="anthropic",
    )
    meter.tracker.record_manual(
        model="gpt-4o",
        input_tokens=200,
        output_tokens=80,
        provider="openai",
    )
    return meter


@pytest.mark.asyncio
async def test_history_screen_renders_data_table() -> None:
    """History screen should contain a DataTable."""
    meter = _make_meter_with_records()
    screen = HistoryScreen(meter)
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await app.mount(screen)
        table = screen.query_one("#history-table", DataTable)
        assert table is not None


@pytest.mark.asyncio
async def test_history_screen_shows_records() -> None:
    """History screen DataTable should have rows for recorded usage."""
    meter = _make_meter_with_records()
    screen = HistoryScreen(meter)
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await app.mount(screen)
        table = screen.query_one("#history-table", DataTable)
        assert table.row_count >= 2
