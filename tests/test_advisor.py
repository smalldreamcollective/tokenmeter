"""Tests for UsageAdvisor — one test per advisor rule, no TUI dependency."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from tokenmeter._types import Tip, UsageRecord
from tokenmeter.advisor import UsageAdvisor


def _make_record(
    model: str,
    input_tokens: int,
    output_tokens: int,
    provider: str = "anthropic",
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    water_ml: Decimal = Decimal("0"),
    energy_wh: Decimal = Decimal("0"),
) -> UsageRecord:
    """Create a minimal UsageRecord for testing."""
    total_cost = Decimal("0.001")  # placeholder
    return UsageRecord(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        input_cost=total_cost / 2,
        output_cost=total_cost / 2,
        total_cost=total_cost,
        water_ml=water_ml,
        energy_wh=energy_wh,
    )


@pytest.fixture
def advisor() -> UsageAdvisor:
    return UsageAdvisor()


# ------------------------------------------------------------------ #
# Empty / trivial                                                      #
# ------------------------------------------------------------------ #


def test_analyze_empty_returns_no_tips(advisor: UsageAdvisor) -> None:
    tips = advisor.analyze([])
    assert tips == []


# ------------------------------------------------------------------ #
# Rule 1 — Model substitution                                          #
# ------------------------------------------------------------------ #


def test_model_substitution_fires_for_expensive_model_short_output(advisor: UsageAdvisor) -> None:
    """Opus with avg output < 500 tokens should trigger substitution tip."""
    # 10 calls on opus-4-6 with small outputs → well under 500 token average
    records = [
        _make_record("claude-opus-4-6", input_tokens=200, output_tokens=100)
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    cost_tips = [t for t in tips if t.category == "cost" and "Switch" in t.title]
    assert len(cost_tips) >= 1
    tip = cost_tips[0]
    assert "claude-opus-4-6" in tip.title
    assert "claude-sonnet-4-5" in tip.title
    assert tip.potential_saving is not None
    assert tip.potential_saving > Decimal("0")
    assert tip.confidence == "medium"


def test_model_substitution_does_not_fire_for_long_output(advisor: UsageAdvisor) -> None:
    """Models with avg output ≥ 500 tokens should NOT trigger substitution."""
    records = [
        _make_record("claude-opus-4-6", input_tokens=500, output_tokens=800)
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    cost_tips = [t for t in tips if "Switch" in t.title]
    assert cost_tips == []


def test_model_substitution_does_not_fire_for_haiku(advisor: UsageAdvisor) -> None:
    """Haiku has no cheaper alternative — no substitution tip."""
    records = [
        _make_record("claude-haiku-4-5", input_tokens=200, output_tokens=50)
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    switch_tips = [t for t in tips if "Switch" in t.title]
    assert switch_tips == []


# ------------------------------------------------------------------ #
# Rule 2 — Caching opportunity                                         #
# ------------------------------------------------------------------ #


def test_caching_tip_fires_when_large_inputs_no_cache(advisor: UsageAdvisor) -> None:
    """≥20% of calls with large inputs and no cache tokens → caching tip."""
    records = [
        _make_record(
            "claude-sonnet-4-5",
            input_tokens=2000,
            output_tokens=100,
            cache_read_tokens=0,
            cache_write_tokens=0,
        )
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    cache_tips = [t for t in tips if t.category == "caching"]
    assert len(cache_tips) >= 1
    tip = cache_tips[0]
    assert "claude-sonnet-4-5" in tip.title
    assert tip.potential_saving is None  # saving is indeterminate


def test_caching_tip_does_not_fire_when_cache_tokens_used(advisor: UsageAdvisor) -> None:
    """Records with cache tokens already in use → no caching tip."""
    records = [
        _make_record(
            "claude-sonnet-4-5",
            input_tokens=2000,
            output_tokens=100,
            cache_read_tokens=500,
        )
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    cache_tips = [t for t in tips if t.category == "caching"]
    assert cache_tips == []


def test_caching_tip_does_not_fire_when_few_qualify(advisor: UsageAdvisor) -> None:
    """If only <20% of calls have large inputs, no caching tip."""
    # 1 large-input record out of 10 = 10% < 20%
    records = [_make_record("claude-sonnet-4-5", input_tokens=100, output_tokens=50)] * 9
    records += [_make_record("claude-sonnet-4-5", input_tokens=2000, output_tokens=100)]
    tips = advisor.analyze(records)
    cache_tips = [t for t in tips if t.category == "caching"]
    assert cache_tips == []


# ------------------------------------------------------------------ #
# Rule 3 — Energy efficiency                                           #
# ------------------------------------------------------------------ #


def test_energy_tip_fires_for_opus_dominated_usage(advisor: UsageAdvisor) -> None:
    """Opus-class model >30% of calls with energy alternative → energy tip."""
    records = [
        _make_record("claude-opus-4-6", input_tokens=500, output_tokens=200)
        for _ in range(7)
    ] + [
        _make_record("claude-haiku-4-5", input_tokens=200, output_tokens=50)
        for _ in range(3)
    ]
    tips = advisor.analyze(records)
    energy_tips = [t for t in tips if t.category == "energy"]
    assert len(energy_tips) >= 1
    tip = energy_tips[0]
    assert "claude-opus-4-6" in tip.title
    assert "claude-haiku-4-5" in tip.title
    assert tip.potential_saving is None
    assert tip.confidence == "medium"


def test_energy_tip_does_not_fire_for_low_opus_fraction(advisor: UsageAdvisor) -> None:
    """Opus-class model <30% of calls → no energy tip."""
    records = [
        _make_record("claude-opus-4-6", input_tokens=500, output_tokens=200)
        for _ in range(2)
    ] + [
        _make_record("claude-haiku-4-5", input_tokens=200, output_tokens=50)
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    energy_tips = [t for t in tips if t.category == "energy"]
    assert energy_tips == []


# ------------------------------------------------------------------ #
# Rule 4 — Water usage                                                 #
# ------------------------------------------------------------------ #


def test_water_tip_fires_above_threshold_with_opus(advisor: UsageAdvisor) -> None:
    """Total water > 500 mL with Opus-class model → water tip."""
    records = [
        _make_record(
            "claude-opus-4-6",
            input_tokens=10000,
            output_tokens=2000,
            water_ml=Decimal("150"),
        )
        for _ in range(5)
    ]
    tips = advisor.analyze(records)
    water_tips = [t for t in tips if t.category == "water"]
    assert len(water_tips) == 1
    tip = water_tips[0]
    assert tip.confidence == "low"
    assert tip.potential_saving is None


def test_water_tip_does_not_fire_below_threshold(advisor: UsageAdvisor) -> None:
    """Total water < 500 mL → no water tip."""
    records = [
        _make_record(
            "claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            water_ml=Decimal("10"),
        )
        for _ in range(3)
    ]
    tips = advisor.analyze(records)
    water_tips = [t for t in tips if t.category == "water"]
    assert water_tips == []


def test_water_tip_does_not_fire_without_opus(advisor: UsageAdvisor) -> None:
    """High water usage but only Haiku-class models → no water tip."""
    records = [
        _make_record(
            "claude-haiku-4-5",
            input_tokens=100,
            output_tokens=50,
            water_ml=Decimal("200"),
        )
        for _ in range(5)
    ]
    tips = advisor.analyze(records)
    water_tips = [t for t in tips if t.category == "water"]
    assert water_tips == []


# ------------------------------------------------------------------ #
# Rule 5 — Output verbosity                                            #
# ------------------------------------------------------------------ #


def test_verbosity_tip_fires_for_low_ratio(advisor: UsageAdvisor) -> None:
    """input:output ratio < 0.3 consistently → verbosity tip."""
    # ratio = 50/2000 = 0.025, well below 0.3
    records = [
        _make_record("claude-sonnet-4-5", input_tokens=50, output_tokens=2000)
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    verbosity_tips = [t for t in tips if "verbosity" in t.title.lower() or "verbose" in t.title.lower() or "Reduce output" in t.title]
    assert len(verbosity_tips) >= 1
    tip = verbosity_tips[0]
    assert tip.potential_saving is not None
    assert tip.potential_saving > Decimal("0")
    assert tip.confidence == "high"


def test_verbosity_tip_does_not_fire_for_normal_ratio(advisor: UsageAdvisor) -> None:
    """input:output ratio >= 0.3 → no verbosity tip."""
    # ratio = 500/1000 = 0.5, above threshold
    records = [
        _make_record("claude-sonnet-4-5", input_tokens=500, output_tokens=1000)
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    verbosity_tips = [t for t in tips if "Reduce output" in t.title]
    assert verbosity_tips == []


def test_verbosity_tip_requires_min_5_records(advisor: UsageAdvisor) -> None:
    """Fewer than 5 records → no verbosity tip (insufficient data)."""
    records = [
        _make_record("claude-sonnet-4-5", input_tokens=50, output_tokens=2000)
        for _ in range(4)
    ]
    tips = advisor.analyze(records)
    verbosity_tips = [t for t in tips if "Reduce output" in t.title]
    assert verbosity_tips == []


# ------------------------------------------------------------------ #
# Sorting                                                              #
# ------------------------------------------------------------------ #


def test_tips_with_saving_sorted_first(advisor: UsageAdvisor) -> None:
    """Tips with potential_saving appear before tips without."""
    # Create conditions for both a cost tip (has saving) and a water tip (no saving)
    records = [
        _make_record(
            "claude-opus-4-6",
            input_tokens=50,
            output_tokens=50,
            water_ml=Decimal("200"),
        )
        for _ in range(10)
    ]
    tips = advisor.analyze(records)
    if len(tips) >= 2:
        # All tips with saving should appear before those without
        saw_no_saving = False
        for tip in tips:
            if tip.potential_saving is None:
                saw_no_saving = True
            elif saw_no_saving:
                pytest.fail("Tip with saving appeared after tip without saving")


def test_tip_is_frozen_dataclass() -> None:
    """Tip instances should be immutable."""
    tip = Tip(
        category="cost",
        title="Test",
        detail="Test detail",
        potential_saving=Decimal("1.00"),
        confidence="high",
    )
    with pytest.raises(Exception):
        tip.title = "changed"  # type: ignore[misc]
