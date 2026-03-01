from __future__ import annotations

from typing import Any

from tokenmeter._compat import get_tiktoken
from tokenmeter.providers._base import Provider


class AnthropicProvider(Provider):
    """Anthropic provider integration."""

    @property
    def name(self) -> str:
        return "anthropic"

    def count_tokens_local(self, text: str, model: str) -> int:
        # Anthropic doesn't provide a local tokenizer.
        # Use tiktoken cl100k_base as a rough estimate if available.
        tiktoken = get_tiktoken()
        if tiktoken is not None:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        return _heuristic_count(text)

    def extract_usage(self, response: Any) -> dict[str, int]:
        usage = response.usage
        result: dict[str, int] = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        }
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0)
        if cache_read:
            result["cache_read_tokens"] = cache_read
        if cache_creation:
            result["cache_write_tokens"] = cache_creation
        return result

    def extract_model(self, response: Any) -> str:
        return str(response.model)

    def matches_response(self, response: Any) -> bool:
        type_name = type(response).__module__
        return "anthropic" in type_name


def _heuristic_count(text: str) -> int:
    """Rough estimate: ~4 characters per token."""
    return max(1, len(text) // 4)
