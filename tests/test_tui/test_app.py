"""Tests for the root TokenmeterApp — requires textual."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")

from textual.widgets import TabbedContent, TabPane  # noqa: E402

from tokenmeter.tui.app import TokenmeterApp  # noqa: E402


@pytest.mark.asyncio
async def test_app_composes_five_tabs() -> None:
    """The app should render with exactly 5 tabs."""
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        tabs = app.query(TabPane)
        assert len(tabs) == 5


@pytest.mark.asyncio
async def test_app_has_tabbed_content() -> None:
    """The app should contain a TabbedContent widget."""
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        tc = app.query_one(TabbedContent)
        assert tc is not None


@pytest.mark.asyncio
async def test_app_refresh_action_does_not_crash() -> None:
    """Pressing 'r' should trigger refresh without raising."""
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await pilot.press("r")
        # No exception = pass


@pytest.mark.asyncio
async def test_app_quit_action() -> None:
    """Pressing 'q' should quit the app."""
    app = TokenmeterApp(db_path=":memory:")
    async with app.run_test() as pilot:
        await pilot.press("q")
