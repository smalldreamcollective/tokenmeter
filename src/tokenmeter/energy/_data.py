"""Built-in energy data for direct energy consumption tracking.

Energy values are in Wh per million tokens, derived from published benchmarks.
These are rough estimates — actual energy depends on hardware, batch size, etc.
"""

from decimal import Decimal

# Anthropic energy per million tokens (Wh)
ANTHROPIC_ENERGY: dict[str, Decimal] = {
    "claude-opus-4-6": Decimal("900"),
    "claude-opus-4-5": Decimal("900"),
    "claude-opus-4-1": Decimal("900"),
    "claude-opus-4": Decimal("900"),
    "claude-sonnet-4-5": Decimal("450"),
    "claude-sonnet-4": Decimal("450"),
    "claude-haiku-4-5": Decimal("100"),
    "claude-haiku-3-5": Decimal("80"),
    "claude-haiku-3": Decimal("50"),
}

# OpenAI energy per million tokens (Wh)
OPENAI_ENERGY: dict[str, Decimal] = {
    "gpt-5.1": Decimal("500"),
    "gpt-5": Decimal("500"),
    "gpt-5-mini": Decimal("100"),
    "gpt-5-nano": Decimal("30"),
    "gpt-4.1": Decimal("300"),
    "gpt-4.1-mini": Decimal("80"),
    "gpt-4.1-nano": Decimal("30"),
    "gpt-4o": Decimal("300"),
    "gpt-4o-mini": Decimal("50"),
    "o1": Decimal("800"),
    "o3": Decimal("500"),
    "o3-mini": Decimal("200"),
    "o4-mini": Decimal("200"),
}
