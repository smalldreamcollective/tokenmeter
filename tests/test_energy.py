"""Tests for energy tracking: registry, calculator, and Meter integration."""

from decimal import Decimal

import pytest

from tokenmeter._types import ModelEnergyProfile
from tokenmeter.energy import EnergyRegistry
from tokenmeter.energy.calculator import EnergyCalculator

from tests.conftest import make_anthropic_response, make_openai_response


class TestEnergyRegistry:
    def test_builtins_loaded(self):
        registry = EnergyRegistry()
        profile = registry.get("claude-sonnet-4-5")
        assert profile is not None
        assert profile.energy_per_mtok == Decimal("450")

    def test_unknown_returns_none(self):
        registry = EnergyRegistry()
        assert registry.get("unknown-model-xyz") is None

    def test_custom_registration(self):
        registry = EnergyRegistry()
        custom = ModelEnergyProfile(
            model_id="my-model", provider="custom", energy_per_mtok=Decimal("200")
        )
        registry.register(custom)
        result = registry.get("my-model")
        assert result is not None
        assert result.energy_per_mtok == Decimal("200")

    def test_alias_resolution(self):
        registry = EnergyRegistry()
        # Anthropic alias should resolve to the canonical model
        profile = registry.get("claude-sonnet-4-5-20250929")
        assert profile is not None
        assert profile.model_id == "claude-sonnet-4-5"

    def test_list_models_all(self):
        registry = EnergyRegistry()
        all_models = registry.list_models()
        assert len(all_models) > 0

    def test_list_models_by_provider(self):
        registry = EnergyRegistry()
        anthropic_models = registry.list_models(provider="anthropic")
        openai_models = registry.list_models(provider="openai")
        all_models = registry.list_models()
        assert len(anthropic_models) + len(openai_models) == len(all_models)
        assert all(registry.get(m) is not None for m in anthropic_models)

    def test_openai_model_loaded(self):
        registry = EnergyRegistry()
        profile = registry.get("gpt-4o")
        assert profile is not None
        assert profile.energy_per_mtok == Decimal("300")
        assert profile.provider == "openai"

    def test_register_overrides_existing(self):
        registry = EnergyRegistry()
        original = registry.get("claude-sonnet-4-5")
        assert original is not None

        updated = ModelEnergyProfile(
            model_id="claude-sonnet-4-5", provider="anthropic", energy_per_mtok=Decimal("999")
        )
        registry.register(updated)
        result = registry.get("claude-sonnet-4-5")
        assert result is not None
        assert result.energy_per_mtok == Decimal("999")


class TestEnergyCalculator:
    def test_basic_calculation_positive(self):
        calc = EnergyCalculator()
        energy = calc.calculate(
            model="claude-sonnet-4-5", input_tokens=500, output_tokens=500
        )
        assert energy > Decimal("0")

    def test_zero_tokens_returns_zero(self):
        calc = EnergyCalculator()
        energy = calc.calculate(
            model="claude-sonnet-4-5", input_tokens=0, output_tokens=0
        )
        assert energy == Decimal("0")

    def test_unknown_model_returns_zero(self):
        calc = EnergyCalculator()
        energy = calc.calculate(
            model="unknown-model-xyz", input_tokens=1000, output_tokens=500
        )
        assert energy == Decimal("0")

    def test_cache_tokens_contribute(self):
        calc = EnergyCalculator()
        energy_base = calc.calculate(
            model="claude-sonnet-4-5", input_tokens=1000, output_tokens=0
        )
        energy_with_cache = calc.calculate(
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=0,
            cache_read_tokens=500,
            cache_write_tokens=500,
        )
        assert energy_with_cache > energy_base

    def test_decimal_return_type(self):
        calc = EnergyCalculator()
        energy = calc.calculate(
            model="claude-sonnet-4-5", input_tokens=1, output_tokens=0
        )
        assert isinstance(energy, Decimal)

    def test_kwh_conversion(self):
        calc = EnergyCalculator()
        wh = calc.calculate(model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0)
        kwh = calc.calculate_kwh(model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0)
        assert kwh == wh / Decimal("1000")

    def test_estimate_input_energy_positive(self):
        calc = EnergyCalculator()
        energy = calc.estimate_input_energy("Hello, world!", model="claude-sonnet-4-5")
        assert energy > Decimal("0")
        assert isinstance(energy, Decimal)

    def test_formula_correctness(self):
        """1M tokens of claude-sonnet-4-5 (450 Wh/MTok) should yield 450 Wh."""
        calc = EnergyCalculator()
        energy = calc.calculate(
            model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0
        )
        assert energy == Decimal("450")

    def test_formula_correctness_mixed_tokens(self):
        """500k input + 500k output = 1M total tokens → 450 Wh."""
        calc = EnergyCalculator()
        energy = calc.calculate(
            model="claude-sonnet-4-5", input_tokens=500_000, output_tokens=500_000
        )
        assert energy == Decimal("450")

    def test_kwh_formula(self):
        """1M tokens of claude-sonnet-4-5 → 0.45 kWh."""
        calc = EnergyCalculator()
        kwh = calc.calculate_kwh(
            model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0
        )
        assert kwh == Decimal("0.450")

    def test_negative_tokens_treated_as_zero(self):
        calc = EnergyCalculator()
        energy = calc.calculate(
            model="claude-sonnet-4-5", input_tokens=-100, output_tokens=0
        )
        assert energy == Decimal("0")

    def test_custom_registry(self):
        registry = EnergyRegistry()
        profile = ModelEnergyProfile(
            model_id="custom-model", provider="custom", energy_per_mtok=Decimal("1000")
        )
        registry.register(profile)
        calc = EnergyCalculator(registry=registry)
        energy = calc.calculate(model="custom-model", input_tokens=1_000_000, output_tokens=0)
        assert energy == Decimal("1000")


class TestEnergyIntegration:
    def test_energy_wh_stored_in_record(self, meter):
        response = make_anthropic_response(
            model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0
        )
        record = meter.record(response)
        assert record.energy_wh == Decimal("450")

    def test_total_energy_sums_correctly(self, meter):
        r1 = make_anthropic_response(
            model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0
        )
        r2 = make_anthropic_response(
            model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0
        )
        meter.record(r1)
        meter.record(r2)
        total = meter.total_energy()
        assert total == Decimal("900")

    def test_total_energy_filter_by_model(self, meter):
        anthropic_resp = make_anthropic_response(
            model="claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0
        )
        openai_resp = make_openai_response(
            model="gpt-4o", prompt_tokens=1_000_000, completion_tokens=0
        )
        meter.record(anthropic_resp)
        meter.record(openai_resp)

        sonnet_energy = meter.total_energy(model="claude-sonnet-4-5")
        gpt_energy = meter.total_energy(model="gpt-4o")
        assert sonnet_energy == Decimal("450")
        assert gpt_energy == Decimal("300")
        assert meter.total_energy() == Decimal("750")

    def test_estimate_energy_returns_decimal(self, meter):
        energy = meter.estimate_energy("Hello, world!", model="claude-sonnet-4-5")
        assert isinstance(energy, Decimal)
        assert energy > Decimal("0")

    def test_energy_wh_default_zero_for_unknown_model(self, meter):
        # Energy calculator returns 0 for unknown models (no exception)
        energy = meter.energy.calculate(
            model="some-unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )
        assert energy == Decimal("0")

    def test_energy_calculator_accessible_on_meter(self, meter):
        assert hasattr(meter, "energy")
        assert isinstance(meter.energy, EnergyCalculator)

    def test_energy_registry_accessible_on_meter(self, meter):
        assert hasattr(meter, "_energy_registry")
        assert isinstance(meter._energy_registry, EnergyRegistry)
