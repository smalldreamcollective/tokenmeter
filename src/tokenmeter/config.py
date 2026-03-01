"""Persistent configuration for tokenmeter (budgets, settings).

Stored as JSON at ~/.tokenmeter/config.json.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from tokenmeter._types import BudgetConfig

_DEFAULT_PATH = "~/.tokenmeter/config.json"


def load_budgets(config_path: str = _DEFAULT_PATH) -> list[BudgetConfig]:
    """Load saved budget configurations from disk."""
    path = Path(config_path).expanduser()
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [
        BudgetConfig(
            limit=Decimal(b["limit"]),
            period=b["period"],
            scope=b.get("scope", "global"),
            action=b.get("action", "warn"),
        )
        for b in data.get("budgets", [])
    ]


def save_budgets(budgets: list[BudgetConfig], config_path: str = _DEFAULT_PATH) -> None:
    """Save budget configurations to disk."""
    path = Path(config_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve other config keys if file exists
    data: dict[str, Any] = {}
    if path.exists():
        data = json.loads(path.read_text())

    data["budgets"] = [
        {
            "limit": str(b.limit),
            "period": b.period,
            "scope": b.scope,
            "action": b.action,
        }
        for b in budgets
    ]
    path.write_text(json.dumps(data, indent=2) + "\n")
