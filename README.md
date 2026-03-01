# tokenmeter

Track, budget, and understand the cost of your AI API calls.

## Installation

```bash
# Core (zero dependencies)
uv pip install tokenmeter

# With CLI
uv pip install "tokenmeter[cli]"        # adds click

# With accurate token counting
uv pip install "tokenmeter[openai]"     # adds tiktoken
uv pip install "tokenmeter[anthropic]"  # adds anthropic SDK
uv pip install "tokenmeter[all]"        # CLI + both providers

# With interactive terminal dashboard
uv pip install "tokenmeter[tui]"        # adds textual + plotext
```

## Quick Start

```python
import tokenmeter

meter = tokenmeter.Meter()

# Estimate cost before calling an API
cost = meter.estimate("Explain quantum computing", model="claude-sonnet-4-5")
print(f"Estimated input cost: ${cost}")

# Record actual usage from an API response
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
record = meter.record(response)
print(f"This call cost: ${record.total_cost}")

# Query spending
print(f"Session total: ${meter.total()}")
print(meter.summary(group_by="model"))
```

Works the same way with OpenAI:

```python
import openai
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)
record = meter.record(response)
```

## Budgets & Alerts

```python
meter = tokenmeter.Meter(storage="sqlite")

# Set spending limits
meter.set_budget(limit=10.00, period="daily", action="block")
meter.set_budget(limit=100.00, period="monthly", action="warn")

# Get notified at thresholds
meter.alerts.set_thresholds([0.5, 0.8, 0.95])
meter.on_alert(lambda status, msg: print(f"ALERT: {msg}"))

# Check before making expensive calls
estimated = meter.estimate(long_prompt, model="claude-opus-4-6")
if meter.budget.would_exceed(estimated):
    print("Would exceed budget — switching to cheaper model")

# Enforce hard limits (raises BudgetExceededError)
meter.budget.enforce(estimated)
```

**Budget periods:** `"daily"`, `"weekly"`, `"monthly"`, `"total"`

**Budget actions:** `"warn"` (log to stderr) or `"block"` (raise `BudgetExceededError`)

## Storage Backends

```python
# In-memory (default) — fast, lost on exit
meter = tokenmeter.Meter(storage="memory")

# SQLite — persistent, queryable
meter = tokenmeter.Meter(storage="sqlite", db_path="~/.tokenmeter/usage.db")

# JSON Lines — simple file, easy to inspect
meter = tokenmeter.Meter(storage="jsonl", path="./usage.jsonl")
```

## Filtering & Tags

```python
# Tag your API calls
meter.record(response, feature="chatbot", env="production", user_id="alice")

# Filter spending
meter.total(provider="anthropic")
meter.total(model="claude-sonnet-4-5")
meter.total(user_id="alice")
meter.total(tags={"feature": "chatbot"})

# Aggregate
meter.summary(group_by="model")
meter.summary(group_by="provider")
meter.summary(group_by="user_id")
```

## Adding Custom Providers

```python
from tokenmeter.providers._base import Provider
from tokenmeter import Meter, ModelPricing
from decimal import Decimal

class GeminiProvider(Provider):
    @property
    def name(self):
        return "google"

    def count_tokens_local(self, text, model):
        return len(text) // 4  # heuristic

    def extract_usage(self, response):
        return {
            "input_tokens": response.usage_metadata.prompt_token_count,
            "output_tokens": response.usage_metadata.candidates_token_count,
        }

    def extract_model(self, response):
        return response.model_version

    def matches_response(self, response):
        return "google" in type(response).__module__

meter = Meter()
meter._provider_registry.register(GeminiProvider())
meter._pricing.register(ModelPricing(
    model_id="gemini-2.0-flash",
    provider="google",
    input_per_mtok=Decimal("0.10"),
    output_per_mtok=Decimal("0.40"),
))
```

## Standalone Cost Calculation

You can use the cost calculator directly without tracking:

```python
from tokenmeter import CostCalculator

calc = CostCalculator()
cost = calc.calculate(model="gpt-4o", input_tokens=1500, output_tokens=500)
print(f"Cost: ${cost}")

# Itemized breakdown
details = calc.calculate_detailed(model="claude-opus-4-6", input_tokens=10000, output_tokens=5000)
print(f"Input: ${details['input_cost']}, Output: ${details['output_cost']}")
```

## API Reference

### `Meter` (main entry point)

| Method | Description |
|--------|-------------|
| `Meter(storage, session_id, user_id)` | Create a meter. Storage: `"memory"`, `"sqlite"`, `"jsonl"` |
| `.estimate(text, model)` | Estimate input cost for text |
| `.record(response, user_id, **tags)` | Record actual usage from API response |
| `.total(**filters)` | Get total spending (filterable) |
| `.summary(group_by)` | Aggregate by `"model"`, `"provider"`, `"user_id"`, `"session_id"` |
| `.set_budget(limit, period, action)` | Set a spending limit |
| `.check_budget()` | Check all budget statuses |
| `.on_alert(callback)` | Register alert callback `(BudgetStatus, str) -> None` |

### Sub-components (accessible via `meter.*`)

| Component | Description |
|-----------|-------------|
| `meter.cost` | `CostCalculator` — stateless cost math |
| `meter.tokens` | `TokenCounter` — local + API-based token counting |
| `meter.tracker` | `UsageTracker` — record/query/aggregate usage |
| `meter.budget` | `BudgetManager` — limits & enforcement |
| `meter.alerts` | `AlertManager` — thresholds & callbacks |

## Supported Models

**Anthropic:** Claude Opus 4.6, 4.5, 4.1, 4 | Sonnet 4.5, 4 | Haiku 4.5, 3.5, 3

**OpenAI:** GPT-5.1, 5, 5-mini, 5-nano | GPT-4.1, 4.1-mini, 4.1-nano | GPT-4o, 4o-mini | o3, o3-mini, o4-mini, o1

## CLI

Install with `uv pip install "tokenmeter[cli]"` to get the `tokenmeter` command.

```bash
# Send a prompt and track the cost
tokenmeter prompt "Explain quantum computing" --model claude-sonnet-4-5
echo "Long prompt..." | tokenmeter prompt --model gpt-4o --system "Be concise"

# Estimate cost without sending
tokenmeter estimate "Your prompt text here" --model claude-opus-4-6

# View spending
tokenmeter usage                         # total spending
tokenmeter usage --by model              # grouped by model
tokenmeter usage --by provider           # grouped by provider

# View individual records
tokenmeter history                       # last 20 records
tokenmeter history --limit 50 --provider anthropic

# Manage budgets
tokenmeter budget set 10.00 --period daily --action block
tokenmeter budget set 100.00 --period monthly
tokenmeter budget list                   # show all budgets with status
tokenmeter budget remove 0              # remove by index

# List supported models with pricing
tokenmeter models
tokenmeter models --provider anthropic

# Clear usage data
tokenmeter clear
```

### API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
# then edit .env with your keys
```

Load the keys before running CLI commands:

```bash
# Option A — source once per shell session
source .env && tokenmeter prompt "Hello" --model claude-3-5-haiku-20241022

# Option B — pass the file to uv run (no sourcing needed)
uv run --env-file .env tokenmeter prompt "Hello" --model claude-3-5-haiku-20241022
```

`.env` is gitignored and will never be committed.

Run `tokenmeter --help` for full command reference, or `tokenmeter.help()` in a Python REPL.
