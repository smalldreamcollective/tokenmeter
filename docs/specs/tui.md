# Spec: tokenmeter TUI + Token Advisor

## Motivation

tokenmeter has a full Python API and Click CLI but no interactive interface. Users who want to
explore usage history, monitor budgets, or understand spending patterns must construct CLI queries
manually. This spec adds:

1. **`tokenmeter ui`** — an interactive terminal dashboard built with Textual.
2. **`UsageAdvisor`** — a pure-backend engine that surfaces actionable tips for reducing token
   spend, energy, and water usage.

---

## Target Users

- Developers actively using tokenmeter who want to explore historical usage interactively.
- Teams monitoring AI spend and wanting at-a-glance budget visibility.
- Environmentally-conscious users who want water/energy feedback.

---

## API Design

### New CLI command

```
tokenmeter ui [--db PATH]
```

Launches the Textual TUI dashboard. If `textual` is not installed, prints an install hint.

### `UsageAdvisor`

```python
from tokenmeter.advisor import UsageAdvisor
from tokenmeter.pricing import PricingRegistry
from tokenmeter.energy import EnergyRegistry

advisor = UsageAdvisor(pricing=PricingRegistry(), energy=EnergyRegistry())
tips = advisor.analyze(records)  # list[UsageRecord] → list[Tip]
```

### `Meter.get_tips(since=None)`

```python
meter = tokenmeter.Meter(storage="sqlite")
tips = meter.get_tips()          # all records
tips = meter.get_tips(since=dt)  # filtered by date
```

### `Tip` dataclass (added to `_types.py`)

```python
@dataclass(frozen=True)
class Tip:
    category: str           # "cost" | "energy" | "water" | "caching"
    title: str
    detail: str
    potential_saving: Decimal | None  # estimated monthly USD, or None
    confidence: str         # "high" | "medium" | "low"
```

### `SummaryRow` dataclass (added to `_types.py`)

```python
@dataclass(frozen=True)
class SummaryRow:
    total_cost: Decimal
    total_input_tokens: int
    total_output_tokens: int
    total_water_ml: Decimal
    total_energy_wh: Decimal
    call_count: int
```

### `UsageTracker.get_summary_detailed(group_by)` (added to `tracker.py`)

Returns `dict[str, SummaryRow]` — full aggregated metrics grouped by model, provider, etc.

---

## Data Model Changes

| Type | Change |
|---|---|
| `_types.py` | Add `Tip` frozen dataclass |
| `_types.py` | Add `SummaryRow` frozen dataclass |
| `tracker.py` | Add `get_summary_detailed(group_by)` method |
| `__init__.py` | Add `Meter.get_tips(since)` method; export `Tip`, `SummaryRow` |

---

## TUI Architecture

**Framework:** Textual (`textual>=0.60.0`) with ASCII charts via `plotext>=5.2.0`.

**Install:**
```
uv pip install 'tokenmeter[tui]'
```

### Screens (as tabs in `TabbedContent`)

| Tab | Contents |
|---|---|
| History | Scrollable DataTable with model/provider filter inputs |
| Summary | Aggregated DataTable + totals footer, group-by selector |
| Budgets | `BudgetGauge` per budget, "no budgets" fallback |
| Charts | Daily spend line chart + per-model bar chart (plotext) |
| Advisor | ListView of Tips + Markdown detail panel |

### Key Bindings

| Key | Action |
|---|---|
| `r` | Refresh data from storage |
| `q` | Quit |
| `?` | Show keyboard hint notification |
| Arrow keys | Navigate within lists/tables |
| Tab | Switch between tabs |

---

## Advisor Rules

| Rule | Fires when | Confidence |
|---|---|---|
| Model substitution | Expensive model, avg output < 500 tokens, projected saving > $0.10/mo | medium |
| Caching opportunity | >20% of calls on caching-capable model have input >1000 tokens, no cache tokens | medium |
| Energy efficiency | Opus-class model (>400 Wh/MTok) is >30% of calls, Haiku-class alternative exists | medium |
| Water usage | Total water > 500 mL and Opus-class usage detected | low |
| Output verbosity | input:output ratio < 0.3 consistently (at least 5 records) | high |

---

## Edge Cases

- **No data:** All screens handle empty record sets gracefully (show helpful message).
- **No budgets:** Budget screen shows a "no budgets" message with CLI hint.
- **Unknown models:** Advisor skips rules that require pricing/energy data for unknown models.
- **Missing plotext:** Charts screen falls back to a plain text table.
- **Missing textual:** `tokenmeter ui` prints an install hint instead of crashing.
- **`:memory:` DB:** TUI supports in-memory storage for testing (data not persisted).

---

## Files Added / Modified

See the Architecture section of CLAUDE.md for the full file listing.
