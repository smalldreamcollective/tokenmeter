import stat
from decimal import Decimal

from tokenmeter._types import BudgetConfig
from tokenmeter.config import load_budgets, save_budgets


def _make_budget(**kwargs):
    defaults = dict(limit=Decimal("10.00"), period="daily", scope="global", action="warn")
    defaults.update(kwargs)
    return BudgetConfig(**defaults)


class TestConfig:
    def test_load_budgets_missing_file_returns_empty(self, tmp_path):
        config_path = str(tmp_path / "missing" / "config.json")
        assert load_budgets(config_path) == []

    def test_save_and_load_budgets_round_trips(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        budgets = [_make_budget(), _make_budget(period="monthly", scope="user:abc")]
        save_budgets(budgets, config_path)

        loaded = load_budgets(config_path)
        assert loaded == budgets

    def test_save_budgets_preserves_other_config_keys(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text('{"other_key": "value"}')

        save_budgets([_make_budget()], str(config_path))

        import json

        data = json.loads(config_path.read_text())
        assert data["other_key"] == "value"
        assert "budgets" in data

    def test_config_file_and_dir_have_restrictive_permissions(self, tmp_path):
        config_path = tmp_path / "data" / "config.json"
        save_budgets([_make_budget()], str(config_path))

        assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(config_path.parent.stat().st_mode) == 0o700
