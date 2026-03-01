# tokenmeter TUI Dashboard

An interactive terminal dashboard for exploring usage history, monitoring budgets, and receiving
optimization tips.

## Installation

```bash
uv pip install 'tokenmeter[tui]'
```

Requires Python 3.12+, `textual>=0.60.0`, and `plotext>=5.2.0`.

## Launch

```bash
# Default database (~/.tokenmeter/usage.db)
tokenmeter ui

# Custom database path
tokenmeter ui --db /path/to/usage.db
```

## Tabs

### History

A scrollable table of all recorded API calls, sorted most-recent first. Use the filter inputs at
the top to narrow by model name or provider.

Columns: Timestamp, Model, Provider, Input tokens, Output tokens, Cost, Water, Energy.

### Summary

Aggregated totals grouped by a chosen dimension (Model, Provider, User ID, Session ID). Use the
dropdown selector to change the grouping. A totals footer shows combined metrics across all groups.

### Budgets

Displays each configured budget as a progress bar showing current utilization. Colour coding:

- **Green** — under 80%
- **Yellow** — 80–99%
- **Red** — exceeded

If no budgets are configured, a hint for the `tokenmeter budget set` command is shown.

### Charts

ASCII charts rendered by plotext:

- **Daily Spending** — line chart of cost per day over the last 30 days.
- **Cost by Model** — bar chart comparing spending per model over the last 30 days.

Falls back to a plain text table if plotext is not installed.

### Advisor

The **Usage Advisor** analyses your last 30 days of usage and surfaces actionable tips in five
categories:

| Icon | Category | Description |
|------|----------|-------------|
| 💰 | cost | Model substitution or output verbosity tips |
| ⚡ | energy | Switch to a lower-energy model |
| 💧 | water | Reduce water footprint |
| 🗄 | caching | Enable prompt caching |

Select a tip in the left panel to see full detail and estimated savings in the right panel.

Tips are sorted by estimated monthly saving (highest first). Tips with no quantified saving appear
after those that have one.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `r` | Refresh all data from storage |
| `q` | Quit |
| `?` | Show keyboard hint notification |
| `Tab` | Switch between tabs (or use mouse) |
| Arrow keys | Navigate within lists and tables |

## Using `get_tips()` Programmatically

The `UsageAdvisor` backend is available without the TUI:

```python
from datetime import datetime, timedelta
import tokenmeter

meter = tokenmeter.Meter(storage="sqlite")

# Analyse last 30 days
since = datetime.now() - timedelta(days=30)
tips = meter.get_tips(since=since)

for tip in tips:
    saving = f" (~${tip.potential_saving:.2f}/mo)" if tip.potential_saving else ""
    print(f"[{tip.category}] {tip.title}{saving}")
    print(f"  {tip.detail}")
    print()
```

Or use `UsageAdvisor` directly:

```python
from tokenmeter.advisor import UsageAdvisor
from tokenmeter.pricing import PricingRegistry
from tokenmeter.energy import EnergyRegistry

advisor = UsageAdvisor(
    pricing=PricingRegistry(),
    energy=EnergyRegistry(),
)
tips = advisor.analyze(meter.tracker.get_records())
```

## `SummaryRow` and `get_summary_detailed()`

The tracker exposes richer aggregation:

```python
summary = meter.tracker.get_summary_detailed(group_by="model")
for model, row in summary.items():
    print(f"{model}: {row.call_count} calls, ${row.total_cost:.4f}")
```

`SummaryRow` fields: `total_cost`, `total_input_tokens`, `total_output_tokens`,
`total_water_ml`, `total_energy_wh`, `call_count`.
