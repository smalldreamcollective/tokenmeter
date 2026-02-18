from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from tokenmeter._types import UsageRecord
from tokenmeter.storage._base import StorageBackend

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_records (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    input_cost TEXT NOT NULL,
    output_cost TEXT NOT NULL,
    total_cost TEXT NOT NULL,
    session_id TEXT,
    user_id TEXT,
    tags TEXT,
    is_estimate INTEGER DEFAULT 0,
    water_ml TEXT DEFAULT '0',
    energy_wh TEXT DEFAULT '0'
);
CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_provider ON usage_records(provider);
CREATE INDEX IF NOT EXISTS idx_session ON usage_records(session_id);
CREATE INDEX IF NOT EXISTS idx_user ON usage_records(user_id);
"""


class SQLiteStorage(StorageBackend):
    """SQLite persistent storage backend. Uses Python's built-in sqlite3 module."""

    def __init__(self, db_path: str = "~/.tokenmeter/usage.db") -> None:
        path = Path(db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            # Migrate: add water_ml column if missing (pre-water databases)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(usage_records)").fetchall()}
            if "water_ml" not in columns:
                conn.execute("ALTER TABLE usage_records ADD COLUMN water_ml TEXT DEFAULT '0'")
            if "energy_wh" not in columns:
                conn.execute("ALTER TABLE usage_records ADD COLUMN energy_wh TEXT DEFAULT '0'")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def save(self, record: UsageRecord) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO usage_records
                (id, timestamp, provider, model, input_tokens, output_tokens,
                 cache_read_tokens, cache_write_tokens, input_cost, output_cost,
                 total_cost, session_id, user_id, tags, is_estimate, water_ml, energy_wh)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    record.timestamp.isoformat(),
                    record.provider,
                    record.model,
                    record.input_tokens,
                    record.output_tokens,
                    record.cache_read_tokens,
                    record.cache_write_tokens,
                    str(record.input_cost),
                    str(record.output_cost),
                    str(record.total_cost),
                    record.session_id,
                    record.user_id,
                    json.dumps(record.tags) if record.tags else None,
                    int(record.is_estimate),
                    str(record.water_ml),
                    str(record.energy_wh),
                ),
            )

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
        conditions: list[str] = []
        params: list[str] = []

        if provider is not None:
            conditions.append("provider = ?")
            params.append(provider)
        if model is not None:
            conditions.append("model = ?")
            params.append(model)
        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
        if session_id is not None:
            conditions.append("session_id = ?")
            params.append(session_id)
        if since is not None:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())
        if until is not None:
            conditions.append("timestamp <= ?")
            params.append(until.isoformat())

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM usage_records{where} ORDER BY timestamp"

        with self._lock, self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()

        records = [_row_to_record(row) for row in rows]

        # Filter by tags in Python (JSON field not easily queryable in SQL)
        if tags is not None:
            records = [
                r for r in records if all(r.tags.get(k) == v for k, v in tags.items())
            ]
        return records

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM usage_records")


def _row_to_record(row: sqlite3.Row) -> UsageRecord:
    tags_str = row["tags"]
    return UsageRecord(
        id=row["id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        provider=row["provider"],
        model=row["model"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        cache_read_tokens=row["cache_read_tokens"],
        cache_write_tokens=row["cache_write_tokens"],
        input_cost=Decimal(row["input_cost"]),
        output_cost=Decimal(row["output_cost"]),
        total_cost=Decimal(row["total_cost"]),
        session_id=row["session_id"],
        user_id=row["user_id"],
        tags=json.loads(tags_str) if tags_str else {},
        is_estimate=bool(row["is_estimate"]),
        water_ml=Decimal(row["water_ml"]) if row["water_ml"] else Decimal("0"),
        energy_wh=Decimal(row["energy_wh"]) if row["energy_wh"] else Decimal("0"),
    )
