import stat
import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from tokenmeter._types import UsageRecord
from tokenmeter.storage.json_file import JsonFileStorage


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
    path = str(tmp_path / "test.jsonl")
    return JsonFileStorage(path=path)


class TestJsonFileStorage:
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

    def test_file_and_dir_have_restrictive_permissions(self, tmp_path):
        path = tmp_path / "data" / "test.jsonl"
        storage = JsonFileStorage(path=str(path))
        storage.save(_make_record())
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700

    def test_query_by_provider(self, storage):
        storage.save(_make_record(provider="anthropic"))
        storage.save(_make_record(provider="openai"))
        results = storage.query(provider="openai")
        assert len(results) == 1

    def test_clear(self, storage):
        storage.save(_make_record())
        storage.clear()
        assert len(storage.query()) == 0

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "persist.jsonl")
        storage1 = JsonFileStorage(path=path)
        record = _make_record()
        storage1.save(record)

        storage2 = JsonFileStorage(path=path)
        results = storage2.query()
        assert len(results) == 1
        assert results[0].id == record.id

    def test_water_ml_serialization(self, storage):
        record = _make_record(water_ml=Decimal("12.345"))
        storage.save(record)
        results = storage.query()
        assert results[0].water_ml == Decimal("12.345")

    def test_water_ml_default_fallback(self, storage):
        record = _make_record()
        storage.save(record)
        results = storage.query()
        assert results[0].water_ml == Decimal("0")
