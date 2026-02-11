from __future__ import annotations

import asyncio
import os
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
        return cls(
            api_url=require_env("FRANKFURTER_API_URL"),
            base_currency=require_env("BASE_CURRENCY"),
            api_currencies=tuple(
                c.strip() for c in require_env("API_CURRENCIES").split(",") if c.strip()
            ),
            usd_azn_peg=float(require_env("USD_AZN_PEG")),
        )

    def get_fx_rates(self, timeout: int = 10) -> Dict:
        params = {
            "from": self.base_currency,
            "to": ",".join(self.api_currencies),
        }

        response = requests.get(self.api_url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        if "rates" not in data:
            raise FXServiceError("FX response missing 'rates' field")

        return data

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
        rates = {k: float(v) for k, v in rates_data.get("rates", {}).items()}

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
async def send_telegram_message(message: str) -> None:
    bot_token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")

    bot = telegram.Bot(token=bot_token)

    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except TypeError:
        # Fallback for sync telegram implementations
        await asyncio.to_thread(bot.send_message, chat_id, message)


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

        print("✅ Notification sent successfully")

    except (requests.RequestException, FXServiceError, ConfigError) as exc:
        print(f"❌ Error: {exc}")
        raise


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
