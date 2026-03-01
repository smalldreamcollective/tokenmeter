"""UsageAdvisor — pure backend that analyzes usage records and surfaces actionable tips.

Zero TUI dependency. Instantiated with PricingRegistry and EnergyRegistry.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from tokenmeter._types import Tip, UsageRecord
from tokenmeter.energy import EnergyRegistry
from tokenmeter.pricing import PricingRegistry

# Models with caching support (have cache_read pricing)
_CACHING_CAPABLE_MODELS: frozenset[str] = frozenset(
    {
        "claude-opus-4-6",
        "claude-opus-4-5",
        "claude-opus-4-1",
        "claude-opus-4",
        "claude-sonnet-4-5",
        "claude-sonnet-4",
        "claude-haiku-4-5",
        "claude-haiku-3-5",
        "claude-haiku-3",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4o",
        "gpt-4o-mini",
        "o3",
        "o3-mini",
        "o4-mini",
        "o1",
    }
)

# Thresholds
_OPUS_ENERGY_WH_PER_MTOK = Decimal("400")  # above = "Opus-class"
_HAIKU_ENERGY_WH_PER_MTOK = Decimal("150")  # below = "Haiku-class"
_WATER_TIP_THRESHOLD_ML = Decimal("500")
_CACHING_INPUT_THRESHOLD = 1000  # tokens
_CACHING_MIN_FRACTION = 0.20  # 20% of calls must qualify
_OUTPUT_VERBOSITY_RATIO = Decimal("0.3")  # input:output < 0.3
_MODEL_SUBSTITUTION_MIN_SAVING = Decimal("0.10")  # projected saving > $0.10/mo
_MODEL_SUBSTITUTION_MAX_AVG_OUTPUT = 500  # avg output < 500 tokens
_ENERGY_OPUS_FRACTION = 0.30  # Opus >30% of calls

# Cheaper alternatives by model (canonical model_id → cheaper alternative model_id)
_CHEAPER_ALTERNATIVES: dict[str, str] = {
    "claude-opus-4-6": "claude-sonnet-4-5",
    "claude-opus-4-5": "claude-sonnet-4-5",
    "claude-opus-4-1": "claude-sonnet-4",
    "claude-opus-4": "claude-sonnet-4",
    "claude-sonnet-4-5": "claude-haiku-4-5",
    "claude-sonnet-4": "claude-haiku-4-5",
    "gpt-5.1": "gpt-5-mini",
    "gpt-5": "gpt-5-mini",
    "gpt-4.1": "gpt-4.1-mini",
    "gpt-4o": "gpt-4o-mini",
    "o1": "o4-mini",
    "o3": "o3-mini",
}

# Energy-efficient alternatives (Opus-class → Haiku-class)
_ENERGY_ALTERNATIVES: dict[str, str] = {
    "claude-opus-4-6": "claude-haiku-4-5",
    "claude-opus-4-5": "claude-haiku-4-5",
    "claude-opus-4-1": "claude-haiku-4-5",
    "claude-opus-4": "claude-haiku-4-5",
    "o1": "gpt-4o-mini",
    "gpt-5.1": "gpt-5-nano",
    "gpt-5": "gpt-5-nano",
}

# Approximate calls per month (daily active use)
_CALLS_PER_MONTH_MULTIPLIER = 30.0


class UsageAdvisor:
    """Analyzes usage records and produces actionable optimization tips.

    Pure backend — no TUI dependency. Safe to instantiate anywhere.
    """

    def __init__(
        self,
        pricing: PricingRegistry | None = None,
        energy: EnergyRegistry | None = None,
    ) -> None:
        self._pricing = pricing or PricingRegistry()
        self._energy = energy or EnergyRegistry()

    def analyze(self, records: list[UsageRecord]) -> list[Tip]:
        """Return a list of tips ordered by estimated impact (highest first).

        Args:
            records: List of usage records to analyze (typically last 30 days).

        Returns:
            List of Tip objects. Empty if no actionable findings.
        """
        if not records:
            return []

        tips: list[Tip] = []
        tips.extend(self._model_substitution_tips(records))
        tips.extend(self._caching_opportunity_tips(records))
        tips.extend(self._energy_efficiency_tips(records))
        tips.extend(self._water_usage_tips(records))
        tips.extend(self._output_verbosity_tips(records))

        # Sort: tips with a potential_saving first (descending), then others
        def _sort_key(t: Tip) -> tuple[int, Decimal]:
            if t.potential_saving is not None:
                return (0, -t.potential_saving)
            return (1, Decimal("0"))

        tips.sort(key=_sort_key)
        return tips

    # ------------------------------------------------------------------ #
    # Rule 1 — Model substitution                                          #
    # ------------------------------------------------------------------ #

    def _model_substitution_tips(self, records: list[UsageRecord]) -> list[Tip]:
        """Fire when expensive model used with short outputs AND cheaper alternative exists."""
        tips: list[Tip] = []

        # Group records by model
        by_model: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in records:
            by_model[r.model].append(r)

        for model, model_records in by_model.items():
            alt_model = _CHEAPER_ALTERNATIVES.get(model)
            if alt_model is None:
                continue

            avg_output = sum(r.output_tokens for r in model_records) / len(model_records)
            if avg_output >= _MODEL_SUBSTITUTION_MAX_AVG_OUTPUT:
                continue

            # Estimate current monthly cost rate
            try:
                current_pricing = self._pricing.get(model)
                alt_pricing = self._pricing.get(alt_model)
            except Exception:
                continue

            # Use average token counts to project saving
            avg_input = sum(r.input_tokens for r in model_records) / len(model_records)
            calls_per_month = len(model_records) * _CALLS_PER_MONTH_MULTIPLIER

            current_cost_per_call = (
                Decimal(str(avg_input)) * current_pricing.input_per_mtok / Decimal("1_000_000")
                + Decimal(str(avg_output)) * current_pricing.output_per_mtok / Decimal("1_000_000")
            )
            alt_cost_per_call = (
                Decimal(str(avg_input)) * alt_pricing.input_per_mtok / Decimal("1_000_000")
                + Decimal(str(avg_output)) * alt_pricing.output_per_mtok / Decimal("1_000_000")
            )
            monthly_saving = (current_cost_per_call - alt_cost_per_call) * Decimal(
                str(calls_per_month)
            )

            if monthly_saving < _MODEL_SUBSTITUTION_MIN_SAVING:
                continue

            tips.append(
                Tip(
                    category="cost",
                    title=f"Switch {model} → {alt_model} for short responses",
                    detail=(
                        f"Your average output for {model} is {avg_output:.0f} tokens — well within "
                        f"the capability range of {alt_model}, which costs significantly less. "
                        f"Switching could save ~${monthly_saving:.2f}/month at your current usage rate."
                    ),
                    potential_saving=monthly_saving.quantize(Decimal("0.01")),
                    confidence="medium",
                )
            )

        return tips

    # ------------------------------------------------------------------ #
    # Rule 2 — Caching opportunity                                         #
    # ------------------------------------------------------------------ #

    def _caching_opportunity_tips(self, records: list[UsageRecord]) -> list[Tip]:
        """Fire when caching-capable model has large inputs but no cache tokens used."""
        tips: list[Tip] = []

        by_model: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in records:
            by_model[r.model].append(r)

        for model, model_records in by_model.items():
            # Resolve alias to canonical model
            try:
                pricing = self._pricing.get(model)
                canonical = pricing.model_id
            except Exception:
                canonical = model

            if canonical not in _CACHING_CAPABLE_MODELS:
                continue

            qualifying = [
                r
                for r in model_records
                if r.input_tokens >= _CACHING_INPUT_THRESHOLD
                and r.cache_read_tokens == 0
                and r.cache_write_tokens == 0
            ]
            fraction = len(qualifying) / len(model_records)
            if fraction < _CACHING_MIN_FRACTION:
                continue

            pct = int(fraction * 100)
            tips.append(
                Tip(
                    category="caching",
                    title=f"Enable prompt caching for {model}",
                    detail=(
                        f"{pct}% of your {model} calls have large inputs (≥{_CACHING_INPUT_THRESHOLD} tokens) "
                        f"but no cache tokens are being used. If your system prompts or context are "
                        f"repeated across calls, enabling prompt caching could substantially reduce "
                        f"input token costs. Savings depend on repetition rate."
                    ),
                    potential_saving=None,
                    confidence="medium",
                )
            )

        return tips

    # ------------------------------------------------------------------ #
    # Rule 3 — Energy efficiency                                           #
    # ------------------------------------------------------------------ #

    def _energy_efficiency_tips(self, records: list[UsageRecord]) -> list[Tip]:
        """Fire when Opus-class models are >30% of calls and a Haiku-class alternative exists."""
        tips: list[Tip] = []

        by_model: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in records:
            by_model[r.model].append(r)

        total_calls = len(records)

        for model, model_records in by_model.items():
            profile = self._energy.get(model)
            if profile is None or profile.energy_per_mtok < _OPUS_ENERGY_WH_PER_MTOK:
                continue

            fraction = len(model_records) / total_calls
            if fraction < _ENERGY_OPUS_FRACTION:
                continue

            alt_model = _ENERGY_ALTERNATIVES.get(model)
            if alt_model is None:
                continue

            alt_profile = self._energy.get(alt_model)
            if alt_profile is None:
                continue

            # Estimate monthly Wh reduction
            avg_tokens = sum(r.input_tokens + r.output_tokens for r in model_records) / len(
                model_records
            )
            calls_per_month = len(model_records) * _CALLS_PER_MONTH_MULTIPLIER
            current_wh = (
                Decimal(str(avg_tokens))
                * profile.energy_per_mtok
                / Decimal("1_000_000")
                * Decimal(str(calls_per_month))
            )
            alt_wh = (
                Decimal(str(avg_tokens))
                * alt_profile.energy_per_mtok
                / Decimal("1_000_000")
                * Decimal(str(calls_per_month))
            )
            saved_wh = current_wh - alt_wh

            tips.append(
                Tip(
                    category="energy",
                    title=f"Replace {model} with {alt_model} to cut energy use",
                    detail=(
                        f"{model} consumes ~{profile.energy_per_mtok} Wh/MTok and accounts for "
                        f"{int(fraction * 100)}% of your calls. Switching to {alt_model} "
                        f"({alt_profile.energy_per_mtok} Wh/MTok) could save ~{saved_wh:.1f} Wh/month."
                    ),
                    potential_saving=None,
                    confidence="medium",
                )
            )

        return tips

    # ------------------------------------------------------------------ #
    # Rule 4 — Water usage                                                 #
    # ------------------------------------------------------------------ #

    def _water_usage_tips(self, records: list[UsageRecord]) -> list[Tip]:
        """Fire when total water > 500 mL and Opus-class usage is detected."""
        total_water = sum(r.water_ml for r in records)
        if total_water <= _WATER_TIP_THRESHOLD_ML:
            return []

        has_opus = any(
            self._energy.get(r.model) is not None
            and (prof := self._energy.get(r.model)) is not None
            and prof.energy_per_mtok >= _OPUS_ENERGY_WH_PER_MTOK
            for r in records
        )

        if not has_opus:
            return []

        return [
            Tip(
                category="water",
                title="Reduce water consumption by choosing lighter models",
                detail=(
                    f"Your recent usage consumed ~{total_water:.0f} mL of water. "
                    f"High-end models (Opus/o1-class) carry a larger water footprint due to their "
                    f"energy requirements. Switching short-context tasks to lighter models "
                    f"(Haiku, GPT-4o-mini) can meaningfully reduce water consumption."
                ),
                potential_saving=None,
                confidence="low",
            )
        ]

    # ------------------------------------------------------------------ #
    # Rule 5 — Output verbosity                                            #
    # ------------------------------------------------------------------ #

    def _output_verbosity_tips(self, records: list[UsageRecord]) -> list[Tip]:
        """Fire when input:output ratio < 0.3 consistently (outputs much larger than inputs)."""
        tips: list[Tip] = []

        by_model: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in records:
            by_model[r.model].append(r)

        for model, model_records in by_model.items():
            # Only consider records with non-zero tokens on both sides
            valid = [r for r in model_records if r.input_tokens > 0 and r.output_tokens > 0]
            if len(valid) < 5:
                continue

            avg_ratio = Decimal(
                str(
                    sum(r.input_tokens / r.output_tokens for r in valid) / len(valid)
                )
            )

            if avg_ratio >= _OUTPUT_VERBOSITY_RATIO:
                continue

            # Estimate saving if output reduced by 30%
            try:
                pricing = self._pricing.get(model)
            except Exception:
                continue

            avg_output = sum(r.output_tokens for r in valid) / len(valid)
            calls_per_month = len(valid) * _CALLS_PER_MONTH_MULTIPLIER
            output_cost_per_call = (
                Decimal(str(avg_output)) * pricing.output_per_mtok / Decimal("1_000_000")
            )
            monthly_saving = output_cost_per_call * Decimal("0.30") * Decimal(
                str(calls_per_month)
            )

            tips.append(
                Tip(
                    category="cost",
                    title=f"Reduce output verbosity for {model}",
                    detail=(
                        f"Your input:output token ratio for {model} is {avg_ratio:.2f} — outputs are "
                        f"much larger than inputs. Adding instructions like 'Be concise' or "
                        f"'Answer in 2-3 sentences' to your system prompt could reduce output "
                        f"tokens by ~30%, saving ~${monthly_saving:.2f}/month."
                    ),
                    potential_saving=monthly_saving.quantize(Decimal("0.01")),
                    confidence="high",
                )
            )

        return tips
