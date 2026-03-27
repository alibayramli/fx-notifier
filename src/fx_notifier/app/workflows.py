from __future__ import annotations

from typing import Any

import requests
import telegram

from fx_notifier.domain.errors import ConfigError, FXServiceError
from fx_notifier.infrastructure.telegram import TelegramNotifier
from fx_notifier.services.fx import FXService
from fx_notifier.services.reporting import calculate_currency_performance, format_message

JSONDict = dict[str, Any]


def build_performance_by_currency(
    service: FXService,
    rates_data: JSONDict,
) -> dict[str, float | None]:
    current_date = rates_data.get("date")
    if not current_date:
        return {}

    normalized = service.normalize_rates(rates_data)
    previous_rates = service.get_previous_rates(service.report_currencies, current_date)

    if "AZN" in service.report_currencies and "USD" in previous_rates:
        previous_rates["AZN"] = round(previous_rates["USD"] * service.usd_azn_peg, 6)

    performance_by_currency: dict[str, float | None] = {}
    for currency in service.report_currencies:
        performance_by_currency[currency] = calculate_currency_performance(
            normalized.get(currency),
            previous_rates.get(currency),
        )

    return performance_by_currency


async def run_notification_workflow(
    service: FXService | None = None,
    notifier: TelegramNotifier | None = None,
) -> str:
    service = service or FXService.from_env()
    notifier = notifier or TelegramNotifier.from_env()

    rates_data = service.get_fx_rates()
    performance_by_currency: dict[str, float | None] = {}

    try:
        performance_by_currency = build_performance_by_currency(service, rates_data)
    except (FXServiceError, ValueError, requests.RequestException):
        performance_by_currency = {}

    message = format_message(
        rates_data,
        service=service,
        performance_by_currency=performance_by_currency,
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
