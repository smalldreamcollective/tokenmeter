# CLI

tokenmeter includes a command-line interface for sending prompts, estimating costs, and managing budgets from the terminal.

## Installation

```bash
uv pip install "smalldreamcollective-tokenmeter[cli]"    # adds click
uv pip install "smalldreamcollective-tokenmeter[all]"    # CLI + both provider SDKs
```

Set API keys via environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.

## Commands

### `tokenmeter prompt`

Send a prompt and track the cost.

```bash
tokenmeter prompt "Explain quantum computing" --model claude-sonnet-4-5
tokenmeter prompt "Summarize this" --model gpt-4o --system "Be concise"
echo "Long text..." | tokenmeter prompt --model claude-sonnet-4-5
```

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | Model to use (required) |
| `--provider` | `-p` | Provider override (anthropic/openai) |
| `--max-tokens` | | Max output tokens (default: 1024) |
| `--system` | `-s` | System prompt |
| `--tag` | `-t` | Tag as key=value (repeatable) |
| `--user-id` | | User ID for tracking |

Output includes token counts, cost, and water usage (if > 0).

### `tokenmeter estimate`

Estimate the input cost and water usage without sending a request.

```bash
tokenmeter estimate "Your prompt text" --model claude-opus-4-6
echo "Long prompt..." | tokenmeter estimate --model gpt-4o
```

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | Model to estimate for (required) |

Example output:
```
Model:            claude-sonnet-4-5
Estimated tokens: 5
Estimated cost:   $0.000015
Estimated water:  ~0.0 mL
```

### `tokenmeter usage`

Show spending summary.

```bash
tokenmeter usage                        # total spending
tokenmeter usage --by model             # grouped by model
tokenmeter usage --by provider          # grouped by provider
tokenmeter usage --provider anthropic   # filter by provider
tokenmeter usage --since 2026-01-01     # filter by date
```

| Option | Description |
|--------|-------------|
| `--by` | Group by: model, provider, user_id, session_id |
| `--provider` | Filter by provider |
| `--model` | Filter by model |
| `--since` | Start date (YYYY-MM-DD) |
| `--until` | End date (YYYY-MM-DD) |

Shows total water alongside total spending when water data is available.

### `tokenmeter history`

Show individual usage records.

```bash
tokenmeter history                           # last 20 records
tokenmeter history --limit 50                # more records
tokenmeter history --provider anthropic      # filter
tokenmeter history --since 2026-01-01
```

| Option | Short | Description |
|--------|-------|-------------|
| `--limit` | `-n` | Number of records (default: 20) |
| `--provider` | | Filter by provider |
| `--model` | | Filter by model |
| `--user-id` | | Filter by user ID |
| `--since` | | Start date |
| `--until` | | End date |

Includes a Water column showing per-record water usage.

### `tokenmeter budget set`

Set a spending budget.

```bash
tokenmeter budget set 10.00 --period daily --action block
tokenmeter budget set 100.00 --period monthly
tokenmeter budget set 5.00 --scope user:alice
```

| Option | Description | Default |
|--------|-------------|---------|
| `--period` | daily, weekly, monthly, total | total |
| `--scope` | global, user:\<id\>, session:\<id\> | global |
| `--action` | warn, block | warn |

### `tokenmeter budget list`

Show all budgets with current status.

```bash
tokenmeter budget list
```

### `tokenmeter budget remove`

Remove a budget by its index (from `budget list`).

```bash
tokenmeter budget remove 0
```

### `tokenmeter models`

List supported models with pricing.

```bash
tokenmeter models                       # all models
tokenmeter models --provider anthropic  # filter by provider
```

### `tokenmeter clear`

Delete all stored usage data.

```bash
tokenmeter clear          # with confirmation prompt
tokenmeter clear --yes    # skip confirmation
```

## Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--db` | Path to SQLite database | `~/.tokenmeter/usage.db` |
| `--version` | Show version and exit | |
| `--help` | Show help for any command | |

## Storage

The CLI uses SQLite storage by default. All commands read from and write to the same database file (`~/.tokenmeter/usage.db`). Override with `--db`:

```bash
tokenmeter --db /tmp/test.db usage
```
