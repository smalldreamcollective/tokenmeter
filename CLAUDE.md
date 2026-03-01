# CLAUDE.md

Project instructions for Claude Code when working on this repository.

## Project Overview

**tokenmeter** is a Python library for tracking, budgeting, and understanding the cost (and water usage) of AI API calls. It supports Anthropic and OpenAI, with an extensible provider system.

- **License:** MIT
- **Python:** >= 3.12
- **Core dependencies:** Zero (optional extras for CLI, token counting, providers)

## Commands

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_water.py

# Lint
ruff check src/

# Type check
mypy src/

# Install in dev mode
uv pip install -e ".[dev]"
```

## Coding Conventions

- **Formatting:** ruff, line-length 100, target Python 3.12
- **Type checking:** mypy strict mode
- **Money/water values:** Always use `Decimal` (never float) for cost and water calculations
- **Config types:** Use `@dataclass(frozen=True)` for immutable configuration (e.g., `ModelPricing`, `WaterProfile`, `BudgetConfig`)
- **Mutable records:** Use `@dataclass` (not frozen) for `UsageRecord` and runtime state
- **Imports:** Use `from __future__ import annotations` in every module
- **Type unions:** Use `X | None` syntax (not `Optional[X]`)
- **Tests:** pytest, fixtures in `tests/conftest.py`, mock response objects for Anthropic/OpenAI

## Git Workflow

- **Always create a new branch for every feature or bug fix.** Never commit directly to `main`.
- Branch naming: `feat-<feature-name>` for features, `fix-<description>` for bug fixes.
- Open a pull request against `main` when the feature is complete and the verification suite passes.

## New Feature Checklist

Every new feature **must** complete these steps in order:

1. **Spec/PRD** — Create a markdown file in `docs/specs/` describing the feature (motivation, API design, data model changes, edge cases). Name it `docs/specs/<feature-name>.md`.
2. **Unit tests** — Write tests before or alongside the implementation. Add a new test file (`tests/test_<feature>.py`) and update existing test files where the feature touches shared code.
3. **Update documentation** — Update the relevant `docs/<feature>.md` file (or create a new one). Update `CLAUDE.md` architecture section if the file structure changed. Update `README.md` if the public API changed.
4. **Code review** — Run the full verification suite before considering the feature complete:
   ```bash
   ruff check src/          # lint
   mypy src/                # type check
   pytest tests/            # all tests pass
   ```
   Review the diff for correctness, security issues, and adherence to coding conventions.
5. **Sources & references** — Create `docs/references/<feature-name>.md` listing every external resource (papers, documentation, APIs, articles, benchmarks) consulted during design and implementation. Include URLs, titles, authors where available, and a brief note on what was used from each source. This applies to web searches, API docs, academic papers, blog posts, and any other material that informed decisions.

Do not skip steps. A feature is not done until all five are complete.

## Architecture

```
src/tokenmeter/
├── __init__.py          # Meter facade — main entry point, wires everything together
├── _types.py            # All dataclasses, enums, and exceptions (incl. Tip, SummaryRow)
├── advisor.py           # UsageAdvisor — pure tip logic, no TUI dependency
├── cost.py              # CostCalculator — stateless cost math
├── tokens.py            # TokenCounter — local token counting
├── tracker.py           # UsageTracker — record/query/aggregate usage
├── budget.py            # BudgetManager — spending limits & enforcement
├── alerts.py            # AlertManager — threshold callbacks
├── cli.py               # Click-based CLI (optional `cli` extra)
├── config.py            # Budget config persistence (~/.tokenmeter/config.json)
├── pricing/
│   ├── __init__.py      # PricingRegistry — model price lookup
│   └── _data.py         # Built-in pricing tables (Anthropic, OpenAI)
├── providers/
│   ├── __init__.py      # ProviderRegistry — auto-detect from responses
│   ├── _base.py         # Abstract Provider base class
│   ├── anthropic.py     # Anthropic provider
│   └── openai.py        # OpenAI provider
├── storage/
│   ├── __init__.py      # create_storage() factory
│   ├── _base.py         # Abstract StorageBackend
│   ├── memory.py        # In-memory (default)
│   ├── sqlite.py        # SQLite persistent
│   └── json_file.py     # JSON Lines file
├── water/
│   ├── __init__.py      # WaterRegistry — model energy lookup
│   ├── _data.py         # Built-in energy tables (Wh per million tokens)
│   └── calculator.py    # WaterCalculator — water usage estimation
├── energy/
│   ├── __init__.py      # EnergyRegistry — model energy lookup (independent of water/)
│   ├── _data.py         # Built-in energy tables (Wh per million tokens)
│   └── calculator.py    # EnergyCalculator — direct Wh/kWh energy estimation
└── tui/                 # Optional TUI (requires tokenmeter[tui])
    ├── __init__.py      # Exports TokenmeterApp; import guard for textual
    ├── app.py           # Root App — TabbedContent with 5 tabs, refresh on 'r'
    ├── tokenmeter.tcss  # Layout + color theming
    ├── screens/
    │   ├── history.py   # Scrollable DataTable of UsageRecords + filters
    │   ├── summary.py   # Aggregated totals by model/provider
    │   ├── budget.py    # ProgressBar per budget, "no budgets" fallback
    │   ├── charts.py    # Spending over time + per-model bar chart
    │   └── advisor.py   # ListView of Tips + Markdown detail panel
    └── widgets/
        ├── budget_gauge.py  # Reusable single-budget ProgressBar + label
        └── spark_chart.py   # plotext wrapper → Static widget
```

## Key Patterns

- **Registry pattern:** `PricingRegistry`, `WaterRegistry`, `EnergyRegistry`, `ProviderRegistry` all follow the same pattern — load builtins, support custom registration, resolve aliases
- **Facade pattern:** `Meter` class in `__init__.py` wires together all subsystems and exposes a simplified API
- **Storage abstraction:** Three backends (memory, sqlite, jsonl) behind `StorageBackend` ABC, selected via `create_storage()` factory
- **Provider auto-detection:** `ProviderRegistry.detect(response)` inspects `__module__` to identify Anthropic vs OpenAI response objects
- **Water is best-effort:** `WaterRegistry.get()` returns `None` for unknown models (unlike `PricingRegistry.get()` which raises `UnknownModelError`). Water calculation returns `Decimal("0")` when a model isn't recognized.
- **Energy is best-effort:** `EnergyRegistry.get()` follows the same pattern as `WaterRegistry` — returns `None` for unknown models, `EnergyCalculator` returns `Decimal("0")`. Energy and water are fully independent modules.
- **Advisor is pure backend:** `UsageAdvisor` in `advisor.py` has zero TUI dependency. It can be imported and used anywhere without `textual` installed.
- **TUI is optional:** The `tui/` package is gated behind `textual` import guards. The `tokenmeter ui` CLI command prints a helpful install message if textual is missing.

## Test Helpers

Mock response objects live in `tests/conftest.py`:
- `make_anthropic_response(model, input_tokens, output_tokens, ...)` — fake Anthropic message
- `make_openai_response(model, prompt_tokens, completion_tokens, ...)` — fake OpenAI chat completion

These set `__module__` so that provider auto-detection works without installing the actual SDK.
