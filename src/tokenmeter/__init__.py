"""tokenmeter — Track, budget, and understand the cost of your AI API calls."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from tokenmeter._types import (
    AlertThreshold,
    BudgetConfig,
    BudgetExceededError,
    BudgetStatus,
    ModelEnergyProfile,
    ModelPricing,
    ModelWaterProfile,
    SummaryRow,
    Tip,
    UnknownModelError,
    UsageRecord,
    WaterProfile,
)
from tokenmeter.alerts import AlertManager
from tokenmeter.budget import BudgetManager
from tokenmeter.cost import CostCalculator
from tokenmeter.energy import EnergyRegistry
from tokenmeter.energy.calculator import EnergyCalculator
from tokenmeter.pricing import PricingRegistry
from tokenmeter.providers import ProviderRegistry
from tokenmeter.storage import create_storage
from tokenmeter.storage._base import StorageBackend
from tokenmeter.tokens import TokenCounter
from tokenmeter.tracker import UsageTracker
from tokenmeter.water import WaterRegistry
from tokenmeter.water.calculator import WaterCalculator

__version__ = "0.1.0"

__all__ = [
    "Meter",
    "CostCalculator",
    "TokenCounter",
    "UsageTracker",
    "BudgetManager",
    "AlertManager",
    "PricingRegistry",
    "ProviderRegistry",
    "WaterProfile",
    "WaterCalculator",
    "WaterRegistry",
    "EnergyCalculator",
    "EnergyRegistry",
    "UsageRecord",
    "ModelPricing",
    "ModelWaterProfile",
    "ModelEnergyProfile",
    "BudgetConfig",
    "BudgetStatus",
    "AlertThreshold",
    "UnknownModelError",
    "BudgetExceededError",
    "SummaryRow",
    "Tip",
    "help",
]


_HELP_TEXT = """\
tokenmeter v{version} — Track, budget, and understand the cost of your AI API calls.

QUICK START
-----------
  import tokenmeter

  meter = tokenmeter.Meter()                          # in-memory tracking
  meter = tokenmeter.Meter(storage="sqlite")          # persistent tracking
  meter = tokenmeter.Meter(storage="jsonl")            # JSON Lines file

ESTIMATE COST
-------------
  cost = meter.estimate("your prompt text", model="claude-sonnet-4-5")

RECORD ACTUAL USAGE
--------------------
  # Auto-detects Anthropic or OpenAI from the response object
  record = meter.record(api_response)
  record = meter.record(api_response, user_id="alice", feature="chatbot")

QUERY SPENDING
--------------
  meter.total()                                       # total across all calls
  meter.total(provider="anthropic")                   # filter by provider
  meter.total(model="gpt-4o")                         # filter by model
  meter.total(tags={{"feature": "chatbot"}})            # filter by tags
  meter.summary(group_by="model")                     # aggregate by model

BUDGETS
-------
  meter.set_budget(limit=10.00, period="daily", action="block")
  meter.set_budget(limit=100.00, period="monthly", action="warn")
  meter.budget.would_exceed(estimated_cost)           # check before calling
  meter.budget.enforce(estimated_cost)                # raises BudgetExceededError
  meter.check_budget()                                # list all budget statuses

  Periods: "daily", "weekly", "monthly", "total"
  Actions: "warn" (log to stderr), "block" (raise exception)

ALERTS
------
  meter.alerts.set_thresholds([0.5, 0.8, 0.95])
  meter.on_alert(lambda status, msg: print(msg))

STANDALONE COST CALCULATION
---------------------------
  from tokenmeter import CostCalculator
  calc = CostCalculator()
  cost = calc.calculate(model="gpt-4o", input_tokens=1500, output_tokens=500)
  details = calc.calculate_detailed(model="claude-opus-4-6", input_tokens=10000, output_tokens=5000)

WATER ESTIMATION
----------------
  meter = Meter(water_profile=WaterProfile())       # default U.S. averages
  meter.estimate_water("your prompt", model="claude-sonnet-4-5")
  meter.total_water()                                 # total mL across all calls
  meter.total_water(model="gpt-4o")                   # filter by model

  Custom environmental factors:
    from tokenmeter import WaterProfile
    profile = WaterProfile(pue=Decimal("1.1"), wue_site=Decimal("1.5"), wue_source=Decimal("0.4"))
    meter = Meter(water_profile=profile)

SUPPORTED MODELS
----------------
  Anthropic: Claude Opus 4.6/4.5/4.1/4, Sonnet 4.5/4, Haiku 4.5/3.5/3
  OpenAI:    GPT-5.1/5/5-mini/5-nano, GPT-4.1/4.1-mini/4.1-nano,
             GPT-4o/4o-mini, o3/o3-mini, o4-mini, o1
"""


def help() -> None:
    """Print a quick-reference usage guide for tokenmeter."""
    print(_HELP_TEXT.format(version=__version__))


class Meter:
    """All-in-one facade for AI cost tracking.

    Usage:
        meter = Meter(storage="sqlite")
        record = meter.record(api_response)
        print(f"Cost: ${record.total_cost}")
        print(f"Session total: ${meter.total()}")
    """

    def __init__(
        self,
        storage: str | StorageBackend = "memory",
        session_id: str | None = None,
        user_id: str | None = None,
        water_profile: WaterProfile | None = None,
        **storage_kwargs: str,
    ) -> None:
        self._pricing = PricingRegistry()
        self._provider_registry = ProviderRegistry()
        self._storage = create_storage(storage, **storage_kwargs)
        self._default_user_id = user_id

        self._water_registry = WaterRegistry()
        self.water = WaterCalculator(
            registry=self._water_registry,
            profile=water_profile or WaterProfile(),
        )

        self._energy_registry = EnergyRegistry()
        self.energy = EnergyCalculator(registry=self._energy_registry)

        self.cost = CostCalculator(self._pricing)
        self.tokens = TokenCounter(self._provider_registry)
        self.tracker = UsageTracker(
            storage=self._storage,
            cost_calculator=self.cost,
            providers=self._provider_registry,
            session_id=session_id,
            water_calculator=self.water,
            energy_calculator=self.energy,
        )
        self.budget = BudgetManager(self.tracker)
        self.alerts = AlertManager(self.budget)

    # --- Quick API ---

    def estimate(self, text: str, model: str) -> Decimal:
        """Estimate the input cost of sending this text to a model."""
        return self.cost.estimate_input_cost(text, model)

    def record(
        self,
        response: Any,
        user_id: str | None = None,
        **tags: str,
    ) -> UsageRecord:
        """Record actual usage from a provider API response. Auto-detects provider."""
        uid = user_id or self._default_user_id
        record = self.tracker.record(response, user_id=uid, **tags)
        self.alerts.check_and_notify(user_id=uid)
        return record

    def total(self, **filters: Any) -> Decimal:
        """Get total spending with optional filters."""
        return self.tracker.get_total(**filters)

    def total_water(self, **filters: Any) -> Decimal:
        """Get total water usage (mL) with optional filters."""
        return self.tracker.get_total_water(**filters)

    def estimate_water(self, text: str, model: str) -> Decimal:
        """Estimate the water usage of sending this text as input to a model."""
        return self.water.estimate_input_water(text, model)

    def total_energy(self, **filters: Any) -> Decimal:
        """Get total energy consumption (Wh) with optional filters."""
        return self.tracker.get_total_energy(**filters)

    def estimate_energy(self, text: str, model: str) -> Decimal:
        """Estimate the energy consumption (Wh) of sending this text as input to a model."""
        return self.energy.estimate_input_energy(text, model)

    def summary(self, group_by: str = "model") -> dict[str, Decimal]:
        """Aggregate spending by model, provider, user_id, or session_id."""
        return self.tracker.get_summary(group_by=group_by)

    def set_budget(
        self,
        limit: float | Decimal,
        period: str = "total",
        scope: str = "global",
        action: str = "warn",
    ) -> BudgetConfig:
        """Set a spending limit."""
        return self.budget.set_budget(limit=limit, period=period, scope=scope, action=action)

    def check_budget(self, user_id: str | None = None) -> list[BudgetStatus]:
        """Check all budget statuses."""
        return self.budget.check(user_id=user_id or self._default_user_id)

    def on_alert(self, callback: Callable[[BudgetStatus, str], None]) -> None:
        """Register an alert callback."""
        self.alerts.on_alert(callback)

    def get_tips(self, since: Any = None) -> list[Tip]:
        """Return actionable optimization tips based on recent usage.

        Args:
            since: Optional datetime to filter records (e.g., 30 days ago).
                   Pass None to analyze all stored records.

        Returns:
            List of Tip objects ordered by estimated impact.
        """
        from tokenmeter.advisor import UsageAdvisor

        records = self.tracker.get_records(since=since)
        advisor = UsageAdvisor(pricing=self._pricing, energy=self._energy_registry)
        return advisor.analyze(records)
