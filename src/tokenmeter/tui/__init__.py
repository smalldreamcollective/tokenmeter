"""tokenmeter TUI — interactive terminal dashboard.

Requires the `tui` extra:
    uv pip install 'tokenmeter[tui]'
"""

from __future__ import annotations

try:
    from tokenmeter.tui.app import TokenmeterApp
except ImportError as _exc:
    raise ImportError(
        "Textual is not installed. Run: uv pip install 'tokenmeter[tui]'"
    ) from _exc

__all__ = ["TokenmeterApp"]
