"""Tests for the Advisor screen."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")

from textual.widgets import Static  # noqa: E402

import tokenmeter  # noqa: E402
from tokenmeter.tui.app import TokenmeterApp  # noqa: E402
from tokenmeter.tui.screens.advisor import AdvisorScreen  # noqa: E402


@pytest.mark.asyncio
async def test_advisor_screen_shows_empty_when_no_records() -> None:
    """Advisor screen should show a helpful message when there is no usage data."""
    meter = tokenmeter.Meter(storage="memory")
    screen = AdvisorScreen(meter)
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await app.mount(screen)
        empty = screen.query_one("#advisor-empty", Static)
        assert empty is not None


@pytest.mark.asyncio
async def test_advisor_screen_composes_without_crash() -> None:
    """Advisor screen composes without raising even with minimal usage data."""
    meter = tokenmeter.Meter(storage="memory")
    # Add a few records
    for _ in range(3):
        meter.tracker.record_manual(
            model="claude-sonnet-4-5",
            input_tokens=500,
            output_tokens=100,
            provider="anthropic",
        )
    screen = AdvisorScreen(meter)
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await app.mount(screen)
        # No exception = pass
