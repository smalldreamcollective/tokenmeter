# Energy Tracking

tokenmeter can estimate the electrical energy consumption (in watt-hours) of your AI API calls. This is a direct measurement of energy use, independent of the water estimation feature.

## Quick Start

```python
import tokenmeter

meter = tokenmeter.Meter()

# Record an API call — energy_wh is computed automatically
record = meter.record(api_response)
print(f"Energy: {record.energy_wh} Wh")

# Total energy across all recorded calls
print(f"Total energy: {meter.total_energy()} Wh")

# Estimate energy before making a call
estimated_wh = meter.estimate_energy("Your prompt text here", model="claude-sonnet-4-5")
```

## How It Works

Energy is estimated using published benchmarks for Wh per million tokens (Wh/MTok). All token types (input, output, cache read, cache write) contribute equally.

```
energy_wh = (total_tokens / 1_000_000) * energy_per_mtok
```

For unknown models, `energy_wh` is `Decimal("0")` (best-effort, no exception raised).

## API Reference

### `meter.total_energy(**filters) -> Decimal`

Returns the total energy (Wh) across all recorded calls. Accepts the same filters as `meter.total()`:

```python
meter.total_energy()                          # all calls
meter.total_energy(model="claude-sonnet-4-5") # filter by model
meter.total_energy(provider="anthropic")      # filter by provider
meter.total_energy(user_id="alice")           # filter by user
```

### `meter.estimate_energy(text, model) -> Decimal`

Estimates the energy (Wh) for sending `text` as input to `model`. Uses a ~4 chars/token heuristic.

```python
wh = meter.estimate_energy("Hello, world!", model="gpt-4o")
```

### `meter.energy` — `EnergyCalculator`

Direct access to the energy calculator for more control:

```python
wh  = meter.energy.calculate(model, input_tokens, output_tokens)
kwh = meter.energy.calculate_kwh(model, input_tokens, output_tokens)
wh  = meter.energy.estimate_input_energy(text, model)
```

### `UsageRecord.energy_wh`

Every `UsageRecord` includes an `energy_wh` field of type `Decimal`:

```python
record = meter.record(response)
print(record.energy_wh)  # e.g., Decimal("0.000450")
```

## Standalone Usage

You can use `EnergyCalculator` and `EnergyRegistry` independently:

```python
from tokenmeter.energy import EnergyRegistry
from tokenmeter.energy.calculator import EnergyCalculator
from tokenmeter._types import ModelEnergyProfile
from decimal import Decimal

registry = EnergyRegistry()

# Register a custom model
registry.register(ModelEnergyProfile(
    model_id="my-model",
    provider="custom",
    energy_per_mtok=Decimal("200"),
))

calc = EnergyCalculator(registry=registry)
wh = calc.calculate("my-model", input_tokens=500_000, output_tokens=500_000)
# → Decimal("200") Wh  (1M total tokens × 200 Wh/MTok)
```

## Built-in Energy Data

| Provider | Model | Wh/MTok |
|---|---|---|
| Anthropic | claude-opus-4-6 | 900 |
| Anthropic | claude-opus-4-5 | 900 |
| Anthropic | claude-opus-4-1 | 900 |
| Anthropic | claude-opus-4 | 900 |
| Anthropic | claude-sonnet-4-5 | 450 |
| Anthropic | claude-sonnet-4 | 450 |
| Anthropic | claude-haiku-4-5 | 100 |
| Anthropic | claude-haiku-3-5 | 80 |
| Anthropic | claude-haiku-3 | 50 |
| OpenAI | gpt-5.1 | 500 |
| OpenAI | gpt-5 | 500 |
| OpenAI | gpt-5-mini | 100 |
| OpenAI | gpt-5-nano | 30 |
| OpenAI | gpt-4.1 | 300 |
| OpenAI | gpt-4.1-mini | 80 |
| OpenAI | gpt-4.1-nano | 30 |
| OpenAI | gpt-4o | 300 |
| OpenAI | gpt-4o-mini | 50 |
| OpenAI | o1 | 800 |
| OpenAI | o3 | 500 |
| OpenAI | o3-mini | 200 |
| OpenAI | o4-mini | 200 |

Values are rough estimates based on published benchmarks. Actual energy depends on hardware, batch size, and data centre configuration.

## Relationship to Water Tracking

Energy tracking and water tracking are independent features that share the same Wh/MTok source data but use separate registries and calculators. Water estimation applies additional environmental factors (PUE, WUE) on top of the energy figure; energy tracking returns the raw Wh value directly.
