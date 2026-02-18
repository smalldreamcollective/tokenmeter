from __future__ import annotations

from tokenmeter._types import ModelEnergyProfile
from tokenmeter.pricing._data import ANTHROPIC_ALIASES, OPENAI_ALIASES
from tokenmeter.energy._data import ANTHROPIC_ENERGY, OPENAI_ENERGY


class EnergyRegistry:
    """Central registry for model energy consumption data."""

    def __init__(self) -> None:
        self._models: dict[str, ModelEnergyProfile] = {}
        self._aliases: dict[str, str] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        for model_id, energy in ANTHROPIC_ENERGY.items():
            self._models[model_id] = ModelEnergyProfile(
                model_id=model_id, provider="anthropic", energy_per_mtok=energy
            )
        for model_id, energy in OPENAI_ENERGY.items():
            self._models[model_id] = ModelEnergyProfile(
                model_id=model_id, provider="openai", energy_per_mtok=energy
            )
        self._aliases.update(ANTHROPIC_ALIASES)
        self._aliases.update(OPENAI_ALIASES)

    def get(self, model: str) -> ModelEnergyProfile | None:
        """Look up energy profile for a model. Returns None if not found."""
        resolved = self._resolve(model)
        return self._models.get(resolved)

    def register(self, profile: ModelEnergyProfile) -> None:
        """Register or override energy data for a model."""
        self._models[profile.model_id] = profile

    def list_models(self, provider: str | None = None) -> list[str]:
        """List all known model IDs, optionally filtered by provider."""
        if provider is None:
            return list(self._models.keys())
        return [p.model_id for p in self._models.values() if p.provider == provider]

    def _resolve(self, model: str) -> str:
        """Resolve aliases and normalize model strings."""
        normalized = model.lower().strip()
        return self._aliases.get(normalized, normalized)
