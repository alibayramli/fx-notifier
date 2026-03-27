from __future__ import annotations

from typing import Any

from fx_notifier.app import build_performance_by_currency, main_async, run_notification_workflow
from fx_notifier.config import (
    FXSettings,
    TelegramSettings,
    get_report_currencies,
    optional_env,
    require_env,
)
from fx_notifier.domain import ConfigError, FXServiceError
from fx_notifier.infrastructure import FrankfurterClient, TelegramNotifier, send_telegram_message
from fx_notifier.services import (
    FXService,
    calculate_currency_performance,
    format_message,
    format_percentage_change,
    format_rate,
)


def get_fx_rates() -> dict[str, Any]:
    return FXService.from_env().get_fx_rates()


__all__ = [
    "ConfigError",
    "FXServiceError",
    "FXSettings",
    "TelegramSettings",
    "FXService",
    "FrankfurterClient",
    "TelegramNotifier",
    "build_performance_by_currency",
    "calculate_currency_performance",
    "format_message",
    "format_percentage_change",
    "format_rate",
    "get_fx_rates",
    "get_report_currencies",
    "main_async",
    "optional_env",
    "require_env",
    "run_notification_workflow",
    "send_telegram_message",
]
