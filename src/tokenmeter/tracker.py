from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from tokenmeter._types import SummaryRow, UsageRecord
from tokenmeter.cost import CostCalculator
from tokenmeter.energy.calculator import EnergyCalculator
from tokenmeter.providers import ProviderRegistry
from tokenmeter.storage._base import StorageBackend
from tokenmeter.storage.memory import MemoryStorage
from tokenmeter.water.calculator import WaterCalculator


class UsageTracker:
    """Records and aggregates API usage data."""

    def __init__(
        self,
        storage: StorageBackend | None = None,
        cost_calculator: CostCalculator | None = None,
        providers: ProviderRegistry | None = None,
        session_id: str | None = None,
        water_calculator: WaterCalculator | None = None,
        energy_calculator: EnergyCalculator | None = None,
    ) -> None:
        self._storage = storage or MemoryStorage()
        self._cost = cost_calculator or CostCalculator()
        self._providers = providers or ProviderRegistry()
        self._session_id = session_id or str(uuid.uuid4())
        self._water = water_calculator
        self._energy = energy_calculator

    @property
    def session_id(self) -> str:
        return self._session_id

    def record(
        self,
        response: Any,
        user_id: str | None = None,
        session_id: str | None = None,
        **tags: str,
    ) -> UsageRecord:
        """Record actual usage from a provider API response. Auto-detects provider."""
        provider = self._providers.detect(response)
        usage = provider.extract_usage(response)
        model = provider.extract_model(response)

        input_toks = usage["input_tokens"]
        output_toks = usage["output_tokens"]
        cache_read_toks = usage.get("cache_read_tokens", 0)
        cache_write_toks = usage.get("cache_write_tokens", 0)

        costs = self._cost.calculate_detailed(
            model=model,
            input_tokens=input_toks,
            output_tokens=output_toks,
            cache_read_tokens=cache_read_toks,
            cache_write_tokens=cache_write_toks,
        )

        water_ml = Decimal("0")
        if self._water is not None:
            water_ml = self._water.calculate(
                model=model,
                input_tokens=input_toks,
                output_tokens=output_toks,
                cache_read_tokens=cache_read_toks,
                cache_write_tokens=cache_write_toks,
            )

        energy_wh = Decimal("0")
        if self._energy is not None:
            energy_wh = self._energy.calculate(
                model=model,
                input_tokens=input_toks,
                output_tokens=output_toks,
                cache_read_tokens=cache_read_toks,
                cache_write_tokens=cache_write_toks,
            )

        record = UsageRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            provider=provider.name,
            model=model,
            input_tokens=input_toks,
            output_tokens=output_toks,
            cache_read_tokens=cache_read_toks,
            cache_write_tokens=cache_write_toks,
            input_cost=costs["input_cost"],
            output_cost=costs["output_cost"],
            total_cost=costs["total_cost"],
            session_id=session_id or self._session_id,
            user_id=user_id,
            tags=dict(tags),
            water_ml=water_ml,
            energy_wh=energy_wh,
        )

        self._storage.save(record)
        return record

    def record_manual(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str | None = None,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        user_id: str | None = None,
        session_id: str | None = None,
        is_estimate: bool = False,
        **tags: str,
    ) -> UsageRecord:
        """Record usage from known token counts (not from a response object)."""
        if provider is None:
            provider = _infer_provider(model)

        costs = self._cost.calculate_detailed(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
        )

        water_ml = Decimal("0")
        if self._water is not None:
            water_ml = self._water.calculate(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_write_tokens=cache_write_tokens,
            )

        energy_wh = Decimal("0")
        if self._energy is not None:
            energy_wh = self._energy.calculate(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_write_tokens=cache_write_tokens,
            )

        record = UsageRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            input_cost=costs["input_cost"],
            output_cost=costs["output_cost"],
            total_cost=costs["total_cost"],
            session_id=session_id or self._session_id,
            user_id=user_id,
            tags=dict(tags),
            is_estimate=is_estimate,
            water_ml=water_ml,
            energy_wh=energy_wh,
        )

        self._storage.save(record)
        return record

    def get_total(
        self,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> Decimal:
        """Get total spending with optional filters."""
        records = self._storage.query(
            provider=provider,
            model=model,
            user_id=user_id,
            session_id=session_id,
            since=since,
            until=until,
            tags=tags,
        )
        return sum((r.total_cost for r in records), Decimal("0"))

    def get_total_water(
        self,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> Decimal:
        """Get total water usage (mL) with optional filters."""
        records = self._storage.query(
            provider=provider,
            model=model,
            user_id=user_id,
            session_id=session_id,
            since=since,
            until=until,
            tags=tags,
        )
        return sum((r.water_ml for r in records), Decimal("0"))

    def get_total_energy(
        self,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> Decimal:
        """Get total energy consumption (Wh) with optional filters."""
        records = self._storage.query(
            provider=provider,
            model=model,
            user_id=user_id,
            session_id=session_id,
            since=since,
            until=until,
            tags=tags,
        )
        return sum((r.energy_wh for r in records), Decimal("0"))

    def get_records(
        self,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> list[UsageRecord]:
        """Get individual records matching filters."""
        return self._storage.query(
            provider=provider,
            model=model,
            user_id=user_id,
            session_id=session_id,
            since=since,
            until=until,
            tags=tags,
        )

    def get_summary(self, group_by: str = "model") -> dict[str, Decimal]:
        """Aggregate spending by model, provider, user_id, or session_id."""
        records = self._storage.query()
        groups: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for r in records:
            key = getattr(r, group_by, "unknown") or "unknown"
            groups[key] += r.total_cost
        return dict(groups)

    def get_summary_detailed(self, group_by: str = "model") -> dict[str, SummaryRow]:
        """Aggregate full metrics by model, provider, user_id, or session_id.

        Returns a mapping from group key to a SummaryRow with totals for cost,
        tokens, water, energy, and call count.
        """
        records = self._storage.query()
        accum: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_cost": Decimal("0"),
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_water_ml": Decimal("0"),
                "total_energy_wh": Decimal("0"),
                "call_count": 0,
            }
        )
        for r in records:
            key = getattr(r, group_by, "unknown") or "unknown"
            row = accum[key]
            row["total_cost"] += r.total_cost
            row["total_input_tokens"] += r.input_tokens
            row["total_output_tokens"] += r.output_tokens
            row["total_water_ml"] += r.water_ml
            row["total_energy_wh"] += r.energy_wh
            row["call_count"] += 1
        return {
            key: SummaryRow(
                total_cost=row["total_cost"],
                total_input_tokens=row["total_input_tokens"],
                total_output_tokens=row["total_output_tokens"],
                total_water_ml=row["total_water_ml"],
                total_energy_wh=row["total_energy_wh"],
                call_count=row["call_count"],
            )
            for key, row in accum.items()
        }


def _infer_provider(model: str) -> str:
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    if any(prefix in model_lower for prefix in ("gpt", "o1", "o3", "o4")):
        return "openai"
    return "unknown"
