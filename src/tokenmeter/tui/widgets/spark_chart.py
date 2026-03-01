"""SparkChart — plotext wrapper rendered into a Textual Static widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

try:
    import plotext as plt  # type: ignore[import-untyped]

    _PLOTEXT_AVAILABLE = True
except ImportError:
    _PLOTEXT_AVAILABLE = False


class SparkChart(Widget):
    """Renders an ASCII chart (line or bar) using plotext inside a Static widget.

    Falls back to a plain text table if plotext is not installed.
    """

    def __init__(
        self,
        title: str,
        x_labels: list[str],
        values: list[float],
        bar: bool = False,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._title = title
        self._x_labels = x_labels
        self._values = values
        self._bar = bar

    def compose(self) -> ComposeResult:
        content = self._render_chart()
        yield Static(content, id=f"{self.id}-content" if self.id else None)

    def _render_chart(self) -> str:
        if not _PLOTEXT_AVAILABLE:
            return self._fallback_table()

        if not self._values:
            return "(no data)"

        plt.clf()
        plt.title(self._title)
        plt.theme("dark")
        plt.plot_size(width=80, height=15)

        if self._bar:
            plt.bar(self._x_labels, self._values)
        else:
            plt.plot(self._values)
            if len(self._x_labels) <= 20:
                plt.xticks(
                    list(range(len(self._x_labels))),
                    self._x_labels,
                )

        return plt.build()

    def _fallback_table(self) -> str:
        """Simple text table when plotext is unavailable."""
        if not self._values:
            return "(no data)"
        lines = [self._title, "─" * 40]
        for label, value in zip(self._x_labels, self._values):
            lines.append(f"  {label:<20} {value:.6f}")
        return "\n".join(lines)
