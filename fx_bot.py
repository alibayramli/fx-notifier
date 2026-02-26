from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import requests
import telegram
from dotenv import load_dotenv

# Load .env if present (local dev only; CI is unaffected)
load_dotenv()


# ------------------------------
# Errors
# ------------------------------
class FXServiceError(Exception):
    """Domain-level FX errors."""


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


# ------------------------------
# Config helpers
# ------------------------------
def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def optional_env(name: str, default: str) -> str:
    return os.environ.get(name, default)


# ------------------------------
# FX Service
# ------------------------------
@dataclass
class FXService:
    api_url: str
    base_currency: str
    api_currencies: Iterable[str]
    usd_azn_peg: float

    @classmethod
    def from_env(cls) -> "FXService":
        """
        Build service from environment variables.
        This is the ONLY place where env vars are required.
        """
        api_currencies = tuple(
            c.strip() for c in require_env("API_CURRENCIES").split(",") if c.strip()
        )
        if not api_currencies:
            raise ConfigError("API_CURRENCIES must include at least one currency")

        raw_peg = require_env("USD_AZN_PEG")
        try:
            usd_azn_peg = float(raw_peg)
        except (TypeError, ValueError):
            raise ConfigError("USD_AZN_PEG must be a valid number")

        return cls(
            api_url=require_env("FRANKFURTER_API_URL"),
            base_currency=require_env("BASE_CURRENCY"),
            api_currencies=api_currencies,
            usd_azn_peg=usd_azn_peg,
        )

    def get_fx_rates(
        self, timeout: int = 10, retries: int = 3, backoff_seconds: float = 1.0
    ) -> Dict:
        params = {
            "from": self.base_currency,
            "to": ",".join(self.api_currencies),
        }
        attempts = max(1, retries)
        last_request_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(self.api_url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()

                if "rates" not in data:
                    raise FXServiceError("FX response missing 'rates' field")

                return data
            except requests.RequestException as exc:
                last_request_error = exc
                if attempt < attempts:
                    time.sleep(backoff_seconds * attempt)

        if last_request_error is not None:
            raise last_request_error

        raise FXServiceError("Failed to fetch FX rates")

    def derive_azn_rate(self, rates: Dict[str, float]) -> float:
        eur_usd = rates.get("USD")
        if eur_usd is None:
            raise FXServiceError("USD rate missing; cannot derive AZN")

        try:
            derived = float(eur_usd) * self.usd_azn_peg
        except (TypeError, ValueError):
            raise FXServiceError("Invalid USD rate; cannot derive AZN")

        return round(derived, 6)

    def normalize_rates(
        self, rates_data: Dict, report_currencies: Iterable[str]
    ) -> Dict[str, float]:
        rates: Dict[str, float] = {}
        for currency, value in rates_data.get("rates", {}).items():
            try:
                rates[currency] = float(value)
            except (TypeError, ValueError):
                raise FXServiceError(f"Invalid rate for {currency}: {value!r}")

        if "AZN" in report_currencies:
            rates["AZN"] = self.derive_azn_rate(rates)

        return rates


# ------------------------------
# Public helpers (used by tests)
# ------------------------------
def get_fx_rates() -> Dict:
    """
    Compatibility wrapper for tests.
    """
    service = FXService.from_env()
    return service.get_fx_rates()


def format_message(rates_data: Dict, service: Optional[FXService] = None) -> str:
    if service is None:
        service = FXService.from_env()

    report_currencies = tuple(
        c.strip()
        for c in optional_env("REPORT_CURRENCIES", "USD,HUF,AZN").split(",")
        if c.strip()
    )

    date = rates_data.get("date", "N/A")
    normalized = service.normalize_rates(rates_data, report_currencies)

    lines = [f"FX Rates for {date} (Base: {service.base_currency}):"]

    for currency in report_currencies:
        value = normalized.get(currency)
        if value is None:
            continue

        suffix = " (derived)" if currency == "AZN" else ""
        lines.append(f"- {currency}: {value}{suffix}")

    lines.extend(
        [
            "",
            "Source: Frankfurter API (frankfurter.app). "
            "AZN is derived via EUR->USD * USD->AZN peg.",
            f"Configured USD->AZN peg: {service.usd_azn_peg}",
        ]
    )

    return "\n".join(lines)


# ------------------------------
# Telegram
# ------------------------------
async def send_telegram_message(
    message: str, retries: int = 3, backoff_seconds: float = 1.0
) -> None:
    bot_token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")

    bot = telegram.Bot(token=bot_token)
    attempts = max(1, retries)
    last_error: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            return
        except TypeError:
            # Fallback for sync telegram implementations
            try:
                await asyncio.to_thread(bot.send_message, chat_id, message)
                return
            except Exception as exc:  # pragma: no cover - defensive fallback
                last_error = exc
        except telegram.error.TelegramError as exc:
            last_error = exc

        if attempt < attempts:
            await asyncio.sleep(backoff_seconds * attempt)

    if last_error is not None:
        raise last_error


# ------------------------------
# CLI entrypoint
# ------------------------------
async def _main_async() -> None:
    service = FXService.from_env()

    try:
        rates_data = service.get_fx_rates()
        message = format_message(rates_data, service=service)

        print(message)  # CI visibility
        await send_telegram_message(message)

        print("Notification sent successfully")

    except (
        requests.RequestException,
        telegram.error.TelegramError,
        FXServiceError,
        ConfigError,
    ) as exc:
        print(f"Error: {exc}")
        raise


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
