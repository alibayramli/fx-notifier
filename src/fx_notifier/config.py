from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from fx_notifier.domain.errors import ConfigError

_ENV_LOADED = False


def _load_environment() -> None:
    global _ENV_LOADED

    if not _ENV_LOADED:
        load_dotenv()
        _ENV_LOADED = True


def require_env(name: str) -> str:
    _load_environment()
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def optional_env(name: str, default: str) -> str:
    _load_environment()
    return os.environ.get(name, default).strip()


def _parse_currencies(name: str, raw_value: str) -> tuple[str, ...]:
    currencies = tuple(
        dict.fromkeys(part.strip().upper() for part in raw_value.split(",") if part.strip())
    )
    if not currencies:
        raise ConfigError(f"{name} must include at least one currency")

    invalid = [currency for currency in currencies if len(currency) != 3 or not currency.isalpha()]
    if invalid:
        joined = ", ".join(invalid)
        raise ConfigError(
            f"{name} contains invalid currency codes: {joined}. "
            "Expected 3-letter ISO-style currency codes."
        )

    return currencies


def get_report_currencies() -> tuple[str, ...]:
    return _parse_currencies("REPORT_CURRENCIES", optional_env("REPORT_CURRENCIES", "USD,HUF,AZN"))


@dataclass(frozen=True)
class FXSettings:
    api_url: str
    base_currency: str
    api_currencies: tuple[str, ...]
    report_currencies: tuple[str, ...]
    usd_azn_peg: float

    @classmethod
    def from_env(cls) -> FXSettings:
        base_currency = require_env("BASE_CURRENCY").upper()
        if len(base_currency) != 3 or not base_currency.isalpha():
            raise ConfigError("BASE_CURRENCY must be a 3-letter currency code")

        api_url = require_env("FRANKFURTER_API_URL")
        api_currencies = _parse_currencies("API_CURRENCIES", require_env("API_CURRENCIES"))
        report_currencies = get_report_currencies()

        raw_peg = require_env("USD_AZN_PEG")
        try:
            usd_azn_peg = float(raw_peg)
        except (TypeError, ValueError) as exc:
            raise ConfigError("USD_AZN_PEG must be a valid number") from exc
        if usd_azn_peg <= 0:
            raise ConfigError("USD_AZN_PEG must be greater than zero")

        if "AZN" in report_currencies and "USD" not in api_currencies:
            raise ConfigError(
                "REPORT_CURRENCIES includes AZN, but API_CURRENCIES must include USD to derive AZN"
            )

        unsupported = [
            currency
            for currency in report_currencies
            if currency not in api_currencies and currency not in {base_currency, "AZN"}
        ]
        if unsupported:
            joined = ", ".join(unsupported)
            raise ConfigError(
                "REPORT_CURRENCIES contains unsupported currencies: "
                f"{joined}. Include them in API_CURRENCIES or use a supported derived currency."
            )

        return cls(
            api_url=api_url,
            base_currency=base_currency,
            api_currencies=api_currencies,
            report_currencies=report_currencies,
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
