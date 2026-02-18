# Spec: Energy Tracking Feature

## Motivation

The existing `water/` module estimates water usage from AI API calls, using energy (Wh per million tokens) as an intermediate value before applying environmental conversion factors. Users who want direct visibility into electrical energy consumption — without the environmental coefficients — have no first-class way to get it.

This feature adds an independent `energy/` module that surfaces energy consumption (in watt-hours) directly, following the same registry/calculator/data pattern as `water/`.

## Goals

- Track electrical energy consumption (Wh) per API call.
- Expose `energy_wh` on `UsageRecord` alongside `water_ml`.
- Provide a standalone `EnergyCalculator` usable outside the `Meter` facade.
- Keep energy and water fully independent — different registries, different data files, no shared state.

## Non-Goals

- Converting energy to CO₂ emissions (out of scope for this feature).
- Replacing or refactoring the `water/` module.
- Real-time hardware power measurement.

---

## API Design

### `ModelEnergyProfile` (new type in `_types.py`)

```python
@dataclass(frozen=True)
class ModelEnergyProfile:
    model_id: str
    provider: str
    energy_per_mtok: Decimal  # Wh per million tokens
```

### `EnergyRegistry` (`src/tokenmeter/energy/__init__.py`)

```python
registry = EnergyRegistry()
profile = registry.get("claude-sonnet-4-5")   # ModelEnergyProfile | None
registry.register(ModelEnergyProfile(...))     # custom model
models = registry.list_models(provider="anthropic")
```

- `get(model)` returns `None` for unknown models (best-effort, no exception).
- Alias resolution uses the same alias tables as `PricingRegistry` and `WaterRegistry`.

### `EnergyCalculator` (`src/tokenmeter/energy/calculator.py`)

```python
calc = EnergyCalculator(registry=EnergyRegistry())
energy_wh  = calc.calculate(model, input_tokens, output_tokens)
energy_kwh = calc.calculate_kwh(model, input_tokens, output_tokens)
energy_wh  = calc.estimate_input_energy(text, model)
```

#### Formula

```text
total_tokens = input_tokens + output_tokens + cache_read_tokens + cache_write_tokens
energy_wh    = (total_tokens / 1_000_000) * energy_per_mtok
energy_kwh   = energy_wh / 1000
```

All token types contribute equally (same assumption as `WaterCalculator`).
Returns `Decimal("0")` when model is unknown.

### `Meter` facade additions

```python
meter = Meter()
meter.energy           # EnergyCalculator instance
meter.total_energy()   # sum of energy_wh across all records (Wh)
meter.total_energy(model="claude-sonnet-4-5")
meter.estimate_energy("prompt text", model="claude-sonnet-4-5")  # Wh
```

---

## Data Model Changes

### `UsageRecord`

Add field:
```python
energy_wh: Decimal = Decimal("0")
```

### Storage

**SQLite**: Add `energy_wh TEXT DEFAULT '0'` column + migration (same pattern as `water_ml`).

**JSON Lines**: Serialize/deserialize `energy_wh` string field (same pattern as `water_ml`).

---

## Built-in Energy Data (`_data.py`)

Same Wh/MTok values as `water/_data.py` — an independent copy.

| Model | Wh/MTok |
|---|---|
| claude-opus-4-6 | 900 |
| claude-opus-4-5 | 900 |
| claude-opus-4-1 | 900 |
| claude-opus-4 | 900 |
| claude-sonnet-4-5 | 450 |
| claude-sonnet-4 | 450 |
| claude-haiku-4-5 | 100 |
| claude-haiku-3-5 | 80 |
| claude-haiku-3 | 50 |
| gpt-5.1 | 500 |
| gpt-5 | 500 |
| gpt-5-mini | 100 |
| gpt-5-nano | 30 |
| gpt-4.1 | 300 |
| gpt-4.1-mini | 80 |
| gpt-4.1-nano | 30 |
| gpt-4o | 300 |
| gpt-4o-mini | 50 |
| o1 | 800 |
| o3 | 500 |
| o3-mini | 200 |
| o4-mini | 200 |

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| Unknown model | `EnergyRegistry.get()` returns `None`; calculator returns `Decimal("0")` |
| Zero tokens | Returns `Decimal("0")` |
| Negative tokens | Treated as 0 via `max(0, ...)` guard in calculator |
| `estimate_input_energy` | Uses `max(1, len(text) // 4)` token heuristic |
| Old SQLite databases (no `energy_wh` column) | Migration adds column with `DEFAULT '0'` |
| Old JSONL records (no `energy_wh` key) | `dict.get("energy_wh", "0")` fallback |

---

## File Layout

```text
src/tokenmeter/energy/
├── __init__.py      # EnergyRegistry
├── _data.py         # ANTHROPIC_ENERGY, OPENAI_ENERGY tables
└── calculator.py    # EnergyCalculator
```
