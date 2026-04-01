from __future__ import annotations

from typing import Any

import requests
import telegram

from fx_notifier.domain.errors import ConfigError, FXServiceError
from fx_notifier.infrastructure.telegram import TelegramNotifier
from fx_notifier.services.fx import FXService
from fx_notifier.services.reporting import calculate_currency_performance, format_message

JSONDict = dict[str, Any]
PERFORMANCE_WARNING = "Performance comparison unavailable; sending spot rates only."


def build_performance_by_currency(
    service: FXService,
    rates_data: JSONDict,
) -> dict[str, float | None]:
    current_date = rates_data.get("date")
    if not current_date:
        raise FXServiceError("FX response missing 'date' field")

    current_rates = service.normalize_rates(rates_data)
    previous_rates = service.get_previous_rates(service.report_currencies, current_date)

    if "AZN" in service.report_currencies and "USD" in previous_rates:
        previous_rates["AZN"] = round(previous_rates["USD"] * service.usd_azn_peg, 6)

    performance_by_currency: dict[str, float | None] = {}
    for currency in service.report_currencies:
        performance_by_currency[currency] = calculate_currency_performance(
            current_rates.get(currency),
            previous_rates.get(currency),
        )

    return performance_by_currency


def get_performance_context(
    service: FXService,
    rates_data: JSONDict,
) -> tuple[dict[str, float | None], list[str]]:
    try:
        return build_performance_by_currency(service, rates_data), []
    except (FXServiceError, ValueError, requests.RequestException) as exc:
        print(f"Warning: {exc}")
        return {}, [PERFORMANCE_WARNING]


async def run_notification_workflow(
    service: FXService | None = None,
    notifier: TelegramNotifier | None = None,
) -> str:
    service = service or FXService.from_env()
    notifier = notifier or TelegramNotifier.from_env()

    rates_data = service.get_fx_rates()
    performance_by_currency, warnings = get_performance_context(service, rates_data)

    message = format_message(
        rates_data,
        service=service,
        performance_by_currency=performance_by_currency,
        warnings=warnings,
    )

    print(message)
    await notifier.send_message(message)
    print("Notification sent successfully")
    return message


async def main_async() -> None:
    try:
        await run_notification_workflow()
    except (
        requests.RequestException,
        telegram.error.TelegramError,
        FXServiceError,
        ConfigError,
    ) as exc:
        print(f"Error: {exc}")
        raise
