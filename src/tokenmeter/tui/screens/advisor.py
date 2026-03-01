"""Advisor screen — ListView of Tips with a Markdown detail panel."""

from __future__ import annotations

from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, Markdown, Static

import tokenmeter
from tokenmeter._types import Tip


_CATEGORY_ICONS: dict[str, str] = {
    "cost": "💰",
    "energy": "⚡",
    "water": "💧",
    "caching": "🗄",
}

_CONFIDENCE_LABELS: dict[str, str] = {
    "high": "[HIGH]",
    "medium": "[MED]",
    "low": "[LOW]",
}


class TipItem(ListItem):
    """A single tip in the list."""

    def __init__(self, tip: Tip, index: int) -> None:
        super().__init__()
        self._tip = tip
        self._index = index

    def compose(self) -> ComposeResult:
        icon = _CATEGORY_ICONS.get(self._tip.category, "•")
        conf = _CONFIDENCE_LABELS.get(self._tip.confidence, "")
        saving = (
            f"  ~${self._tip.potential_saving:.2f}/mo"
            if self._tip.potential_saving is not None
            else ""
        )
        yield Static(f"{icon} {conf} {self._tip.title}{saving}", classes=f"tip-category-{self._tip.category}")


class AdvisorScreen(Widget):
    """Displays usage optimization tips with detail panel."""

    def __init__(self, meter: tokenmeter.Meter) -> None:
        super().__init__()
        self._meter = meter
        self._tips: list[Tip] = []

    def compose(self) -> ComposeResult:
        yield Label("Usage Advisor", classes="section-title")

        since = datetime.now() - timedelta(days=30)
        self._tips = self._meter.get_tips(since=since)

        if not self._tips:
            yield Static(
                "No tips available. Keep using tokenmeter and check back later!\n\n"
                "Tips appear once you have enough usage history (last 30 days).",
                id="advisor-empty",
            )
            return

        with Static(id="advisor-container"):
            list_view = ListView(id="tip-list")
            for i, tip in enumerate(self._tips):
                list_view.append(TipItem(tip, i))
            yield list_view
            yield Markdown(self._tip_markdown(self._tips[0]), id="tip-detail")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        if not isinstance(event.item, TipItem):
            return
        tip = event.item._tip
        detail = self.query_one("#tip-detail", Markdown)
        detail.update(self._tip_markdown(tip))

    @staticmethod
    def _tip_markdown(tip: Tip) -> str:
        icon = _CATEGORY_ICONS.get(tip.category, "•")
        saving_line = (
            f"\n**Estimated saving:** ~${tip.potential_saving:.2f}/month"
            if tip.potential_saving is not None
            else ""
        )
        return (
            f"## {icon} {tip.title}\n\n"
            f"**Category:** {tip.category}  \n"
            f"**Confidence:** {tip.confidence}{saving_line}\n\n"
            f"---\n\n"
            f"{tip.detail}\n"
        )
