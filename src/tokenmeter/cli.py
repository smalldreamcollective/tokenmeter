"""tokenmeter CLI — track, budget, and understand AI API costs from the terminal."""

from __future__ import annotations

import sys
from datetime import datetime
from decimal import Decimal

import click

import tokenmeter
from tokenmeter.config import load_budgets, save_budgets
from tokenmeter.pricing import PricingRegistry


def _get_meter(db: str) -> tokenmeter.Meter:
    """Create a Meter with SQLite storage and load saved budgets."""
    meter = tokenmeter.Meter(storage="sqlite", db_path=db)
    for budget_config in load_budgets():
        meter.budget.set_budget(
            limit=budget_config.limit,
            period=budget_config.period,
            scope=budget_config.scope,
            action=budget_config.action,
        )
    return meter


def _parse_tags(tag_values: tuple[str, ...]) -> dict[str, str]:
    """Parse --tag key=value pairs."""
    tags: dict[str, str] = {}
    for t in tag_values:
        if "=" not in t:
            raise click.BadParameter(f"Tag must be key=value, got: {t!r}")
        k, v = t.split("=", 1)
        tags[k] = v
    return tags


def _infer_provider(model: str) -> str:
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    if any(p in model_lower for p in ("gpt", "o1", "o3", "o4")):
        return "openai"
    raise click.ClickException(
        f"Cannot infer provider for model {model!r}. Use --provider to specify."
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise click.BadParameter(f"Invalid date format: {value!r}. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.")


@click.group()
@click.option("--db", default="~/.tokenmeter/usage.db", help="Path to SQLite database.", show_default=True)
@click.version_option(version=tokenmeter.__version__, prog_name="tokenmeter")
@click.pass_context
def cli(ctx: click.Context, db: str) -> None:
    """tokenmeter — Track, budget, and understand the cost of your AI API calls."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


# ---------- prompt ----------


@cli.command()
@click.argument("text", required=False)
@click.option("--model", "-m", required=True, help="Model to use (e.g., claude-sonnet-4-5, gpt-4o).")
@click.option("--provider", "-p", default=None, help="Provider override (anthropic or openai).")
@click.option("--max-tokens", default=1024, help="Max output tokens.", show_default=True)
@click.option("--system", "-s", default=None, help="System prompt.")
@click.option("--tag", "-t", multiple=True, help="Tag as key=value (repeatable).")
@click.option("--user-id", default=None, help="User ID for tracking.")
@click.pass_context
def prompt(
    ctx: click.Context,
    text: str | None,
    model: str,
    provider: str | None,
    max_tokens: int,
    system: str | None,
    tag: tuple[str, ...],
    user_id: str | None,
) -> None:
    """Send a prompt to an AI model and track the cost.

    Reads from stdin if no TEXT argument is provided.
    """
    if text is None:
        if sys.stdin.isatty():
            raise click.UsageError("Provide prompt text as an argument or pipe from stdin.")
        text = sys.stdin.read().strip()

    if not text:
        raise click.UsageError("Prompt text is empty.")

    tags = _parse_tags(tag)
    provider_name = provider or _infer_provider(model)
    meter = _get_meter(ctx.obj["db"])

    if provider_name == "anthropic":
        response, response_text = _call_anthropic(text, model, max_tokens, system)
    elif provider_name == "openai":
        response, response_text = _call_openai(text, model, max_tokens, system)
    else:
        raise click.ClickException(f"Unknown provider: {provider_name!r}")

    record = meter.tracker.record(response, user_id=user_id, **tags)
    meter.alerts.check_and_notify(user_id=user_id)

    click.echo(response_text)
    click.echo()
    cost_line = (
        f"[{record.model}] "
        f"{record.input_tokens} in / {record.output_tokens} out | "
        f"Cost: ${record.total_cost:.6f}"
    )
    if record.water_ml > 0:
        cost_line += f" | Water: ~{record.water_ml:.1f} mL"
    if record.energy_wh > 0:
        cost_line += f" | Energy: ~{record.energy_wh:.4f} Wh"
    click.echo(click.style(cost_line, fg="cyan"))


def _call_anthropic(text: str, model: str, max_tokens: int, system: str | None):
    try:
        import anthropic
    except ImportError:
        raise click.ClickException(
            "anthropic package not installed. Run: uv pip install anthropic"
        )
    client = anthropic.Anthropic()
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": text}],
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    response_text = response.content[0].text
    return response, response_text


def _call_openai(text: str, model: str, max_tokens: int, system: str | None):
    try:
        import openai
    except ImportError:
        raise click.ClickException(
            "openai package not installed. Run: uv pip install openai"
        )
    client = openai.OpenAI()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": text})
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )
    response_text = response.choices[0].message.content
    return response, response_text


# ---------- estimate ----------


@cli.command()
@click.argument("text", required=False)
@click.option("--model", "-m", required=True, help="Model to estimate cost for.")
@click.pass_context
def estimate(ctx: click.Context, text: str | None, model: str) -> None:
    """Estimate the input cost of a prompt without sending it."""
    if text is None:
        if sys.stdin.isatty():
            raise click.UsageError("Provide prompt text as an argument or pipe from stdin.")
        text = sys.stdin.read().strip()

    meter = _get_meter(ctx.obj["db"])
    token_count = meter.tokens.count_local(text, model=model)
    cost = meter.cost.estimate_input_cost(text, model)
    water = meter.estimate_water(text, model)
    energy = meter.estimate_energy(text, model)

    click.echo(f"Model:            {model}")
    click.echo(f"Estimated tokens: {token_count:,}")
    click.echo(f"Estimated cost:   ${cost:.6f}")
    if water > 0:
        click.echo(f"Estimated water:  ~{water:.1f} mL")
    if energy > 0:
        click.echo(f"Estimated energy: ~{energy:.4f} Wh")


# ---------- usage ----------


@cli.command()
@click.option("--by", "group_by", default=None, help="Group by: model, provider, user_id, session_id.")
@click.option("--provider", default=None, help="Filter by provider.")
@click.option("--model", default=None, help="Filter by model.")
@click.option("--since", default=None, help="Start date (YYYY-MM-DD).")
@click.option("--until", default=None, help="End date (YYYY-MM-DD).")
@click.pass_context
def usage(
    ctx: click.Context,
    group_by: str | None,
    provider: str | None,
    model: str | None,
    since: str | None,
    until: str | None,
) -> None:
    """Show spending summary."""
    meter = _get_meter(ctx.obj["db"])
    since_dt = _parse_datetime(since)
    until_dt = _parse_datetime(until)

    if group_by:
        summary = meter.tracker.get_summary(group_by=group_by)
        if not summary:
            click.echo("No usage data recorded yet.")
            return
        click.echo(f"Spending by {group_by}:")
        click.echo(f"{'─' * 50}")
        for key, cost in sorted(summary.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  {key:<30} ${cost:.6f}")
        click.echo(f"{'─' * 50}")
        click.echo(f"  {'Total':<30} ${sum(summary.values()):.6f}")
    else:
        total = meter.tracker.get_total(
            provider=provider, model=model, since=since_dt, until=until_dt
        )
        total_water = meter.tracker.get_total_water(
            provider=provider, model=model, since=since_dt, until=until_dt
        )
        total_energy = meter.tracker.get_total_energy(
            provider=provider, model=model, since=since_dt, until=until_dt
        )
        records = meter.tracker.get_records(
            provider=provider, model=model, since=since_dt, until=until_dt
        )
        click.echo(f"Total spending: ${total:.6f}")
        if total_water > 0:
            click.echo(f"Total water:    ~{total_water:.1f} mL")
        if total_energy > 0:
            click.echo(f"Total energy:   ~{total_energy:.4f} Wh")
        click.echo(f"Total requests: {len(records)}")
        if records:
            total_input = sum(r.input_tokens for r in records)
            total_output = sum(r.output_tokens for r in records)
            click.echo(f"Total tokens:   {total_input + total_output:,} ({total_input:,} in / {total_output:,} out)")


# ---------- history ----------


@cli.command()
@click.option("--limit", "-n", default=20, help="Number of records to show.", show_default=True)
@click.option("--provider", default=None, help="Filter by provider.")
@click.option("--model", default=None, help="Filter by model.")
@click.option("--user-id", default=None, help="Filter by user ID.")
@click.option("--since", default=None, help="Start date (YYYY-MM-DD).")
@click.option("--until", default=None, help="End date (YYYY-MM-DD).")
@click.pass_context
def history(
    ctx: click.Context,
    limit: int,
    provider: str | None,
    model: str | None,
    user_id: str | None,
    since: str | None,
    until: str | None,
) -> None:
    """Show individual usage records."""
    meter = _get_meter(ctx.obj["db"])
    records = meter.tracker.get_records(
        provider=provider,
        model=model,
        user_id=user_id,
        since=_parse_datetime(since),
        until=_parse_datetime(until),
    )

    if not records:
        click.echo("No usage records found.")
        return

    # Show most recent first, limited
    records = sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]

    click.echo(f"{'Timestamp':<20} {'Model':<25} {'In':>8} {'Out':>8} {'Cost':>12} {'Water':>10} {'Energy':>12}")
    click.echo(f"{'─' * 99}")
    for r in records:
        ts = r.timestamp.strftime("%Y-%m-%d %H:%M")
        water_str = f"~{r.water_ml:.1f} mL" if r.water_ml > 0 else "—"
        energy_str = f"~{r.energy_wh:.4f} Wh" if r.energy_wh > 0 else "—"
        click.echo(f"{ts:<20} {r.model:<25} {r.input_tokens:>8,} {r.output_tokens:>8,} ${r.total_cost:>10.6f} {water_str:>10} {energy_str:>12}")


# ---------- budget ----------


@cli.group()
def budget() -> None:
    """Manage spending budgets."""


@budget.command("set")
@click.argument("limit", type=float)
@click.option("--period", default="total", type=click.Choice(["daily", "weekly", "monthly", "total"]), show_default=True)
@click.option("--scope", default="global", help="Scope: global, user:<id>, session:<id>.", show_default=True)
@click.option("--action", default="warn", type=click.Choice(["warn", "block"]), show_default=True)
def budget_set(limit: float, period: str, scope: str, action: str) -> None:
    """Set a spending budget (e.g., tokenmeter budget set 10.00 --period daily)."""
    budgets = load_budgets()
    from tokenmeter._types import BudgetConfig
    config = BudgetConfig(
        limit=Decimal(str(limit)),
        period=period,
        scope=scope,
        action=action,
    )
    budgets.append(config)
    save_budgets(budgets)
    click.echo(f"Budget set: ${config.limit:.2f} {config.period} ({config.scope}, {config.action})")


@budget.command("list")
@click.pass_context
def budget_list(ctx: click.Context) -> None:
    """List all budgets with current status."""
    meter = _get_meter(ctx.obj["db"])
    budgets = meter.budget.list_budgets()

    if not budgets:
        click.echo("No budgets configured.")
        return

    click.echo(f"{'#':<4} {'Limit':>10} {'Period':<10} {'Scope':<15} {'Action':<8} {'Spent':>10} {'Remaining':>10} {'Used':>6}")
    click.echo(f"{'─' * 80}")

    statuses = meter.budget.check()
    for i, status in enumerate(statuses):
        c = status.config
        pct = f"{status.utilization * 100:.0f}%"
        color = "green" if status.utilization < 0.8 else ("yellow" if status.utilization < 1.0 else "red")
        click.echo(
            f"{i:<4} ${c.limit:>9} {c.period:<10} {c.scope:<15} {c.action:<8} "
            f"${status.spent:>9.4f} ${status.remaining:>9.4f} "
            + click.style(f"{pct:>5}", fg=color)
        )


@budget.command("remove")
@click.argument("index", type=int)
def budget_remove(index: int) -> None:
    """Remove a budget by its index number (from 'budget list')."""
    budgets = load_budgets()
    if index < 0 or index >= len(budgets):
        raise click.ClickException(f"Invalid budget index: {index}. Run 'tokenmeter budget list' to see indices.")
    removed = budgets.pop(index)
    save_budgets(budgets)
    click.echo(f"Removed budget: ${removed.limit} {removed.period} ({removed.scope})")


# ---------- models ----------


@cli.command()
@click.option("--provider", "-p", default=None, help="Filter by provider (anthropic, openai).")
def models(provider: str | None) -> None:
    """List supported models with pricing."""
    registry = PricingRegistry()
    model_ids = registry.list_models(provider=provider)

    if not model_ids:
        click.echo("No models found.")
        return

    click.echo(f"{'Model':<25} {'Provider':<12} {'Input/MTok':>12} {'Output/MTok':>12} {'Cache Read':>12}")
    click.echo(f"{'─' * 75}")

    for model_id in sorted(model_ids):
        pricing = registry.get(model_id)
        cache_read = f"${pricing.cache_read_per_mtok}" if pricing.cache_read_per_mtok else "—"
        click.echo(
            f"{pricing.model_id:<25} {pricing.provider:<12} "
            f"${pricing.input_per_mtok:>10} ${pricing.output_per_mtok:>10} "
            f"{cache_read:>11}"
        )


# ---------- clear ----------


@cli.command()
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def clear(ctx: click.Context, yes: bool) -> None:
    """Clear all stored usage data."""
    if not yes:
        click.confirm("This will delete all usage records. Continue?", abort=True)
    meter = _get_meter(ctx.obj["db"])
    meter.tracker._storage.clear()
    click.echo("All usage data cleared.")


if __name__ == "__main__":
    cli()
