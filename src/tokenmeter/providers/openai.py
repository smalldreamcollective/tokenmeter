from __future__ import annotations

from typing import Any

from tokenmeter._compat import get_tiktoken
from tokenmeter.providers._base import Provider


class OpenAIProvider(Provider):
    """OpenAI provider integration."""

    @property
    def name(self) -> str:
        return "openai"

    def count_tokens_local(self, text: str, model: str) -> int:
        tiktoken = get_tiktoken()
        if tiktoken is not None:
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        return _heuristic_count(text)

    def extract_usage(self, response: Any) -> dict[str, int]:
        usage = response.usage
        result: dict[str, int] = {
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
        }
        if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
            cached = getattr(usage.prompt_tokens_details, "cached_tokens", 0)
            if cached:
                result["cache_read_tokens"] = cached
        return result

    def extract_model(self, response: Any) -> str:
        return str(response.model)

    def matches_response(self, response: Any) -> bool:
        type_name = type(response).__module__
        return "openai" in type_name


def _heuristic_count(text: str) -> int:
    """Rough estimate: ~4 characters per token."""
    return max(1, len(text) // 4)
