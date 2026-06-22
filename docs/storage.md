# Storage Backends

tokenmeter supports three storage backends for persisting usage records.

## Choosing a Backend

| Backend | Persistence | Best for |
|---------|-------------|----------|
| `"memory"` | None (lost on exit) | Testing, short-lived scripts |
| `"sqlite"` | SQLite file | Production, CLI, long-term tracking |
| `"jsonl"` | JSON Lines file | Simple persistence, easy to inspect/parse |

## Usage

### Via the Meter facade

```python
import tokenmeter

# In-memory (default)
meter = tokenmeter.Meter(storage="memory")

# SQLite
meter = tokenmeter.Meter(storage="sqlite", db_path="~/.tokenmeter/usage.db")

# JSON Lines
meter = tokenmeter.Meter(storage="jsonl", path="./usage.jsonl")
```

### Via the factory function

```python
from tokenmeter.storage import create_storage

storage = create_storage("sqlite", db_path="/tmp/test.db")
storage = create_storage("jsonl", path="/tmp/test.jsonl")
storage = create_storage("memory")
```

### Passing a custom instance

```python
from tokenmeter.storage.sqlite import SQLiteStorage

storage = SQLiteStorage(db_path="/custom/path.db")
meter = tokenmeter.Meter(storage=storage)
```

## StorageBackend Interface

All backends implement this ABC. Source: `src/tokenmeter/storage/_base.py`

#### `save(record: UsageRecord) -> None`

Persist a single usage record.

#### `query(**filters) -> list[UsageRecord]`

Query records matching filters:

| Filter | Type | Description |
|--------|------|-------------|
| `provider` | `str \| None` | Filter by provider name |
| `model` | `str \| None` | Filter by model ID |
| `user_id` | `str \| None` | Filter by user ID |
| `session_id` | `str \| None` | Filter by session ID |
| `since` | `datetime \| None` | Records after this time |
| `until` | `datetime \| None` | Records before this time |
| `tags` | `dict[str, str] \| None` | Records matching all tags |

#### `clear() -> None`

Delete all stored records.

## Backend Details

### MemoryStorage

Source: `src/tokenmeter/storage/memory.py`

Stores `UsageRecord` objects in a Python list. Fast, no dependencies, no persistence.

### SQLiteStorage

Source: `src/tokenmeter/storage/sqlite.py`

- Default path: `~/.tokenmeter/usage.db`
- Thread-safe (uses `threading.Lock`)
- Indexed on `timestamp`, `provider`, `session_id`, `user_id`
- Decimal values stored as TEXT for precision
- Tags stored as JSON
- Auto-migrates schema (adds new columns like `water_ml` to existing databases)
- Data directory and database file are created with restrictive permissions (`0700`/`0600`) so other local accounts can't read usage history

### JsonFileStorage

Source: `src/tokenmeter/storage/json_file.py`

- Default path: `~/.tokenmeter/usage.jsonl`
- One JSON object per line (JSON Lines format)
- Thread-safe (uses `threading.Lock`)
- Decimal values stored as strings for precision
- Backward-compatible: missing fields use sensible defaults on read
- Data directory and file are created with restrictive permissions (`0700`/`0600`) so other local accounts can't read usage history

## Implementing a Custom Backend

Subclass `StorageBackend` and implement all three methods:

```python
from tokenmeter.storage._base import StorageBackend
from tokenmeter._types import UsageRecord
from datetime import datetime

class RedisStorage(StorageBackend):
    def __init__(self, url: str):
        self._client = redis.Redis.from_url(url)

    def save(self, record: UsageRecord) -> None:
        ...

    def query(self, provider=None, model=None, user_id=None,
              session_id=None, since=None, until=None, tags=None) -> list[UsageRecord]:
        ...

    def clear(self) -> None:
        ...

meter = tokenmeter.Meter(storage=RedisStorage("redis://localhost"))
```
