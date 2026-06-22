from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from tokenmeter._types import UsageRecord
from tokenmeter.storage._base import StorageBackend


class JsonFileStorage(StorageBackend):
    """JSON Lines file storage backend. Each line is a JSON-serialized UsageRecord."""

    def __init__(self, path: str = "~/.tokenmeter/usage.jsonl") -> None:
        self._path = Path(path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)
        self._lock = threading.Lock()

    def save(self, record: UsageRecord) -> None:
        line = json.dumps(_record_to_dict(record))
        with self._lock:
            with open(self._path, "a") as f:
                f.write(line + "\n")
            os.chmod(self._path, 0o600)

    def query(
        self,
        provider: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        tags: dict[str, str] | None = None,
    ) -> list[UsageRecord]:
        records = self._load_all()

        if provider is not None:
            records = [r for r in records if r.provider == provider]
        if model is not None:
            records = [r for r in records if r.model == model]
        if user_id is not None:
            records = [r for r in records if r.user_id == user_id]
        if session_id is not None:
            records = [r for r in records if r.session_id == session_id]
        if since is not None:
            records = [r for r in records if r.timestamp >= since]
        if until is not None:
            records = [r for r in records if r.timestamp <= until]
        if tags is not None:
            records = [
                r for r in records if all(r.tags.get(k) == v for k, v in tags.items())
            ]
        return records

    def clear(self) -> None:
        with self._lock:
            if self._path.exists():
                self._path.unlink()

    def _load_all(self) -> list[UsageRecord]:
        with self._lock:
            if not self._path.exists():
                return []
            with open(self._path) as f:
                lines = f.readlines()
        return [_dict_to_record(json.loads(line)) for line in lines if line.strip()]


def _record_to_dict(record: UsageRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "timestamp": record.timestamp.isoformat(),
        "provider": record.provider,
        "model": record.model,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "cache_read_tokens": record.cache_read_tokens,
        "cache_write_tokens": record.cache_write_tokens,
        "input_cost": str(record.input_cost),
        "output_cost": str(record.output_cost),
        "total_cost": str(record.total_cost),
        "session_id": record.session_id,
        "user_id": record.user_id,
        "tags": record.tags,
        "is_estimate": record.is_estimate,
        "water_ml": str(record.water_ml),
        "energy_wh": str(record.energy_wh),
    }


def _dict_to_record(d: dict[str, Any]) -> UsageRecord:
    return UsageRecord(
        id=d["id"],
        timestamp=datetime.fromisoformat(d["timestamp"]),
        provider=d["provider"],
        model=d["model"],
        input_tokens=d["input_tokens"],
        output_tokens=d["output_tokens"],
        cache_read_tokens=d.get("cache_read_tokens", 0),
        cache_write_tokens=d.get("cache_write_tokens", 0),
        input_cost=Decimal(d["input_cost"]),
        output_cost=Decimal(d["output_cost"]),
        total_cost=Decimal(d["total_cost"]),
        session_id=d.get("session_id"),
        user_id=d.get("user_id"),
        tags=d.get("tags", {}),
        is_estimate=d.get("is_estimate", False),
        water_ml=Decimal(d.get("water_ml", "0")),
        energy_wh=Decimal(d.get("energy_wh", "0")),
    )
