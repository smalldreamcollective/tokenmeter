from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TokenType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    CACHE_READ = "cache_read"
    CACHE_WRITE = "cache_write"


@dataclass(frozen=True)
class ModelPricing:
    """Price per million tokens for a specific model."""

    model_id: str
    provider: str
    input_per_mtok: Decimal
    output_per_mtok: Decimal
    cache_read_per_mtok: Decimal | None = None
    cache_write_per_mtok: Decimal | None = None
    batch_input_per_mtok: Decimal | None = None
    batch_output_per_mtok: Decimal | None = None


@dataclass
class UsageRecord:
    """A single API call's usage data."""

    id: str
    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    session_id: str | None = None
    user_id: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    is_estimate: bool = False
    water_ml: Decimal = Decimal("0")  # estimated water usage in milliliters
    energy_wh: Decimal = Decimal("0")  # estimated energy consumption in watt-hours


@dataclass
class BudgetConfig:
    """Configuration for a spending limit."""

    limit: Decimal
    period: str  # "session", "daily", "weekly", "monthly", "total"
    scope: str = "global"
    action: str = "warn"  # "warn" or "block"


@dataclass
class BudgetStatus:
    """Current state of a budget."""

    config: BudgetConfig
    spent: Decimal
    remaining: Decimal
    utilization: float
    is_exceeded: bool


@dataclass
class AlertThreshold:
    """Threshold at which an alert fires."""

    percentage: float
    message: str | None = None
    triggered: bool = False


@dataclass(frozen=True)
class WaterProfile:
    """Environmental factors for water estimation. Defaults are U.S. averages."""

    pue: Decimal = Decimal("1.2")
    wue_site: Decimal = Decimal("1.8")  # L/kWh, on-site cooling
    wue_source: Decimal = Decimal("0.5")  # L/kWh, upstream electricity


@dataclass(frozen=True)
class ModelWaterProfile:
    """Energy characteristics for a model. energy_per_mtok is Wh per million tokens."""

    model_id: str
    provider: str
    energy_per_mtok: Decimal


@dataclass(frozen=True)
class ModelEnergyProfile:
    """Energy consumption profile for a model. energy_per_mtok is Wh per million tokens."""

    model_id: str
    provider: str
    energy_per_mtok: Decimal


@dataclass(frozen=True)
class Tip:
    """An actionable suggestion for reducing token spend, energy, or water usage."""

    category: str  # "cost" | "energy" | "water" | "caching"
    title: str
    detail: str
    potential_saving: Decimal | None  # estimated monthly USD, or None
    confidence: str  # "high" | "medium" | "low"


@dataclass(frozen=True)
class SummaryRow:
    """Aggregated metrics for a single group (model, provider, etc.)."""

    total_cost: Decimal
    total_input_tokens: int
    total_output_tokens: int
    total_water_ml: Decimal
    total_energy_wh: Decimal
    call_count: int


class UnknownModelError(Exception):
    """Raised when a model ID is not found in the pricing registry."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(f"Unknown model: {model!r}. Register it with PricingRegistry.register().")


class BudgetExceededError(Exception):
    """Raised when a budget with action='block' would be exceeded."""

    def __init__(self, status: BudgetStatus) -> None:
        self.status = status
        super().__init__(
            f"Budget exceeded: ${status.spent} spent of ${status.config.limit} "
            f"({status.config.period} {status.config.scope})"
        )
