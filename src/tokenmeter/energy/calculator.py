from __future__ import annotations

from decimal import Decimal

from tokenmeter.energy import EnergyRegistry

_ONE_MILLION = Decimal("1000000")
_ONE_THOUSAND = Decimal("1000")


class EnergyCalculator:
    """Calculates electrical energy consumption (Wh) for AI model inference."""

    def __init__(self, registry: EnergyRegistry | None = None) -> None:
        self._registry = registry or EnergyRegistry()

    def calculate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> Decimal:
        """Calculate estimated energy consumption in watt-hours. Returns 0 if model unknown."""
        profile = self._registry.get(model)
        if profile is None:
            return Decimal("0")

        total_tokens = (
            max(0, input_tokens)
            + max(0, output_tokens)
            + max(0, cache_read_tokens)
            + max(0, cache_write_tokens)
        )
        if total_tokens <= 0:
            return Decimal("0")

        tokens_in_millions = Decimal(total_tokens) / _ONE_MILLION
        return tokens_in_millions * profile.energy_per_mtok

    def calculate_kwh(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> Decimal:
        """Calculate estimated energy consumption in kilowatt-hours."""
        wh = self.calculate(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
        )
        return wh / _ONE_THOUSAND

    def estimate_input_energy(self, text: str, model: str) -> Decimal:
        """Estimate energy for sending text as input, using ~4 chars per token heuristic."""
        estimated_tokens = max(1, len(text) // 4)
        return self.calculate(model=model, input_tokens=estimated_tokens, output_tokens=0)
