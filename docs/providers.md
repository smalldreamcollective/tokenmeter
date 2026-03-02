# Providers

tokenmeter supports multiple AI providers with automatic response detection.

## Built-in Providers

| Provider | Name | Models |
|----------|------|--------|
| Anthropic | `"anthropic"` | Claude Opus, Sonnet, Haiku families |
| OpenAI | `"openai"` | GPT-5.x, GPT-4.x, GPT-4o, o-series |

## How Auto-Detection Works

When you call `meter.record(response)`, tokenmeter inspects the response object's `__module__` attribute to identify the provider:

- `"anthropic.types"` -> Anthropic
- `"openai.types.chat"` -> OpenAI

No configuration needed — just pass the raw API response.

## Classes

### `ProviderRegistry`

Registry with auto-detection. Source: `src/tokenmeter/providers/__init__.py`

**Methods:**

#### `detect(response) -> Provider`

Auto-detect provider from a response object. Raises `ValueError` if no provider matches.

#### `register(provider: Provider) -> None`

Register a custom provider.

#### `get(name: str) -> Provider`

Get a provider by name. Raises `KeyError` if not found.

#### `list_providers() -> list[str]`

Return all registered provider names.

### `Provider` (ABC)

Base class for provider integrations. Source: `src/tokenmeter/providers/_base.py`

| Method | Returns | Description |
|--------|---------|-------------|
| `name` (property) | `str` | Provider identifier (e.g., `"anthropic"`) |
| `count_tokens_local(text, model)` | `int` | Estimate token count locally |
| `extract_usage(response)` | `dict[str, int]` | Extract token counts from response |
| `extract_model(response)` | `str` | Extract model ID from response |
| `matches_response(response)` | `bool` | Whether this provider handles this response |

`extract_usage()` returns a dict with keys:
- `input_tokens` (required)
- `output_tokens` (required)
- `cache_read_tokens` (optional)
- `cache_write_tokens` (optional)

## Adding a Custom Provider

```python
from tokenmeter.providers._base import Provider
from tokenmeter import Meter, ModelPricing
from decimal import Decimal

class GeminiProvider(Provider):
    @property
    def name(self):
        return "google"

    def count_tokens_local(self, text, model):
        return len(text) // 4  # heuristic fallback

    def extract_usage(self, response):
        return {
            "input_tokens": response.usage_metadata.prompt_token_count,
            "output_tokens": response.usage_metadata.candidates_token_count,
        }

    def extract_model(self, response):
        return response.model_version

    def matches_response(self, response):
        return "google" in type(response).__module__

# Wire it up
meter = Meter()
meter._provider_registry.register(GeminiProvider())
meter._pricing.register(ModelPricing(
    model_id="gemini-2.0-flash",
    provider="google",
    input_per_mtok=Decimal("0.10"),
    output_per_mtok=Decimal("0.40"),
))

# Now meter.record() works with Gemini responses
record = meter.record(gemini_response)
```

## Token Counting

### `TokenCounter`

Source: `src/tokenmeter/tokens.py`

Accessible via `meter.tokens`.

#### `count_local(text, model, provider=None) -> int`

Count tokens locally using the best available tokenizer. Falls back to a heuristic (~4 chars per token) if the provider's tokenizer isn't installed.

```python
count = meter.tokens.count_local("Hello, world!", model="claude-sonnet-4-5")
```

#### `count_messages_local(messages, model, provider=None) -> int`

Count tokens for a list of chat messages, including per-message overhead (~4 tokens each):

```python
messages = [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello!"},
]
count = meter.tokens.count_messages_local(messages, model="gpt-4o")
```

#### `from_response(response) -> dict[str, int]`

Extract actual token usage from an API response:

```python
usage = meter.tokens.from_response(api_response)
# {"input_tokens": 150, "output_tokens": 80, "cache_read_tokens": 0}
```

## Notes

- Provider inference from model name: `"claude"` -> anthropic, `"gpt"/"o1"/"o3"/"o4"` -> openai.
- For accurate token counting, install the provider SDK extras: `uv pip install "smalldreamcollective-tokenmeter[anthropic]"` or `uv pip install "smalldreamcollective-tokenmeter[openai]"`.
