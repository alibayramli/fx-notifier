from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from fx_notifier.domain.errors import ConfigError

load_dotenv()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def optional_env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def get_report_currencies() -> tuple[str, ...]:
    return _parse_csv(optional_env("REPORT_CURRENCIES", "USD,HUF,AZN"))


@dataclass(frozen=True)
class FXSettings:
    api_url: str
    base_currency: str
    api_currencies: tuple[str, ...]
    report_currencies: tuple[str, ...]
    usd_azn_peg: float

    @classmethod
    def from_env(cls) -> FXSettings:
        api_currencies = _parse_csv(require_env("API_CURRENCIES"))
        if not api_currencies:
            raise ConfigError("API_CURRENCIES must include at least one currency")

        raw_peg = require_env("USD_AZN_PEG")
        try:
            usd_azn_peg = float(raw_peg)
        except (TypeError, ValueError) as exc:
            raise ConfigError("USD_AZN_PEG must be a valid number") from exc

        return cls(
            api_url=require_env("FRANKFURTER_API_URL"),
            base_currency=require_env("BASE_CURRENCY"),
            api_currencies=api_currencies,
            report_currencies=get_report_currencies(),
            usd_azn_peg=usd_azn_peg,
        )


@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> TelegramSettings:
        return cls(
            bot_token=require_env("TELEGRAM_BOT_TOKEN"),
            chat_id=require_env("TELEGRAM_CHAT_ID"),
        )
