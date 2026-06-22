import stat
import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from tokenmeter._types import UsageRecord
from tokenmeter.storage.sqlite import SQLiteStorage


def _make_record(**kwargs):
    defaults = dict(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        provider="anthropic",
        model="claude-sonnet-4-5",
        input_tokens=100,
        output_tokens=50,
        input_cost=Decimal("0.0003"),
        output_cost=Decimal("0.00075"),
        total_cost=Decimal("0.00105"),
    )
    defaults.update(kwargs)
    return UsageRecord(**defaults)


@pytest.fixture
def storage(tmp_path):
    db_path = str(tmp_path / "test.db")
    return SQLiteStorage(db_path=db_path)


class TestSQLiteStorage:
    def test_save_and_query(self, storage):
        record = _make_record()
        storage.save(record)
        results = storage.query()
        assert len(results) == 1
        assert results[0].id == record.id

    def test_decimal_precision(self, storage):
        record = _make_record(
            input_cost=Decimal("0.123456789"),
            output_cost=Decimal("0.987654321"),
            total_cost=Decimal("1.111111110"),
        )
        storage.save(record)
        results = storage.query()
        assert results[0].input_cost == Decimal("0.123456789")
        assert results[0].output_cost == Decimal("0.987654321")

    def test_db_file_and_dir_have_restrictive_permissions(self, tmp_path):
        db_path = tmp_path / "data" / "test.db"
        SQLiteStorage(db_path=str(db_path))
        assert stat.S_IMODE(db_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(db_path.parent.stat().st_mode) == 0o700

    def test_query_by_provider(self, storage):
        storage.save(_make_record(provider="anthropic"))
        storage.save(_make_record(provider="openai"))
        results = storage.query(provider="anthropic")
        assert len(results) == 1

    def test_query_by_tags(self, storage):
        storage.save(_make_record(tags={"env": "prod"}))
        storage.save(_make_record(tags={"env": "staging"}))
        results = storage.query(tags={"env": "prod"})
        assert len(results) == 1

    def test_clear(self, storage):
        storage.save(_make_record())
        storage.save(_make_record())
        storage.clear()
        assert len(storage.query()) == 0

    def test_persistence(self, tmp_path):
        db_path = str(tmp_path / "persist.db")
        storage1 = SQLiteStorage(db_path=db_path)
        record = _make_record()
        storage1.save(record)

        # New instance, same file
        storage2 = SQLiteStorage(db_path=db_path)
        results = storage2.query()
        assert len(results) == 1
        assert results[0].id == record.id

    def test_water_ml_persisted(self, storage):
        record = _make_record(water_ml=Decimal("12.345"))
        storage.save(record)
        results = storage.query()
        assert results[0].water_ml == Decimal("12.345")

    def test_water_ml_default(self, storage):
        record = _make_record()
        storage.save(record)
        results = storage.query()
        assert results[0].water_ml == Decimal("0")
