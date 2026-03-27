from __future__ import annotations

from typing import Any

from fx_notifier.services.fx import FXService

JSONDict = dict[str, Any]
GREEN_INDICATOR = "\U0001F7E2"
RED_INDICATOR = "\U0001F534"
NEUTRAL_INDICATOR = "\u26AA"


def format_rate(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def format_percentage_change(change_pct: float | None) -> str:
    if change_pct is None:
        return f"{NEUTRAL_INDICATOR} n/a"

    if change_pct > 0:
        indicator = GREEN_INDICATOR
        sign = "+"
    elif change_pct < 0:
        indicator = RED_INDICATOR
        sign = ""
    else:
        indicator = NEUTRAL_INDICATOR
        sign = ""

    return f"{indicator} {sign}{change_pct:.2f}%"


def calculate_currency_performance(
    current_rate: float | None,
    previous_rate: float | None,
) -> float | None:
    if current_rate is None or previous_rate is None:
        return None
    if current_rate == 0 or previous_rate == 0:
        return None

    return ((previous_rate / current_rate) - 1) * 100


def format_message(
    rates_data: JSONDict,
    service: FXService | None = None,
    performance_by_currency: dict[str, float | None] | None = None,
) -> str:
    service = service or FXService.from_env()
    performance_by_currency = performance_by_currency or {}

    date_text = rates_data.get("date", "N/A")
    normalized = service.normalize_rates(rates_data)
    rate_header = f"1 {service.base_currency}"
    rows: list[tuple[str, str, str]] = []

    for currency in service.report_currencies:
        value = normalized.get(currency)
        if value is None:
            continue

        rows.append(
            (
                currency,
                format_rate(value),
                format_percentage_change(performance_by_currency.get(currency)),
            )
        )

    currency_width = max([len("CCY"), *[len(currency) for currency, _, _ in rows]])
    rate_width = max([len(rate_header), *[len(rate) for _, rate, _ in rows]])

    lines = [
        f"<b>{service.base_currency} FX Update</b> <code>{date_text}</code>",
        "<pre>",
    ]
    lines.append(
        f"{'CCY':<{currency_width}}  {rate_header:>{rate_width}}  {'Perf (CCY vs EUR)'}"
    )
    for currency, rate_text, change_text in rows:
        lines.append(
            f"{currency:<{currency_width}}  {rate_text:>{rate_width}}  {change_text}"
        )
    lines.append("</pre>")

    return "\n".join(lines)
