from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import requests
import telegram
from dotenv import load_dotenv

# Load .env (required)
load_dotenv()


# ------------------------------
# Strict env loading (no defaults)
# ------------------------------
def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


FRANKFURTER_API_URL = require_env("FRANKFURTER_API_URL")
BASE_CURRENCY = require_env("BASE_CURRENCY")

API_CURRENCIES = [
    c.strip() for c in require_env("API_CURRENCIES").split(",") if c.strip()
]

REPORT_CURRENCIES = [
    c.strip() for c in require_env("REPORT_CURRENCIES").split(",") if c.strip()
]

USD_AZN_PEG = float(require_env("USD_AZN_PEG"))


class FXServiceError(Exception):
    pass


@dataclass(frozen=True)
class FXService:
    api_url: str
    base_currency: str
    api_currencies: Iterable[str]
    usd_azn_peg: float

    def get_fx_rates(self, timeout: int = 10) -> Dict:
        """Fetch FX rates from Frankfurter API."""
        params = {
            "from": self.base_currency,
            "to": ",".join(self.api_currencies),
        }

        response = requests.get(self.api_url, params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        if "rates" not in data:
            raise FXServiceError("API response missing 'rates' field")

        return data

    def derive_azn_rate(self, rates: Dict[str, float]) -> float:
        """
        Derive EUR→AZN using:
        EUR/AZN = EUR/USD × USD/AZN
        """
        eur_usd = rates.get("USD")
        if eur_usd is None:
            raise FXServiceError("USD rate missing — cannot derive AZN")

        try:
            eur_usd = float(eur_usd)
        except (TypeError, ValueError):
            raise FXServiceError("USD rate is not numeric")

        return round(eur_usd * self.usd_azn_peg, 6)

    def normalize_rates(self, rates_data: Dict) -> Dict[str, float]:
        """Merge API rates with derived rates."""
        rates = {k: float(v) for k, v in rates_data["rates"].items()}

        if "AZN" in REPORT_CURRENCIES:
            rates["AZN"] = self.derive_azn_rate(rates)

        return rates


# ------------------------------
# Compatibility helpers (tests & workflow)
# ------------------------------
def get_fx_rates() -> Dict:
    service = FXService(
        api_url=FRANKFURTER_API_URL,
        base_currency=BASE_CURRENCY,
        api_currencies=API_CURRENCIES,
        usd_azn_peg=USD_AZN_PEG,
    )
    return service.get_fx_rates()


def format_message(rates_data: Dict, service: Optional[FXService] = None) -> str:
    if service is None:
        service = FXService(
            api_url=FRANKFURTER_API_URL,
            base_currency=BASE_CURRENCY,
            api_currencies=API_CURRENCIES,
            usd_azn_peg=USD_AZN_PEG,
        )

    date = rates_data.get("date", "N/A")
    normalized = service.normalize_rates(rates_data)

    lines = [f"FX Rates for {date} (Base: {service.base_currency}):"]

    for currency in REPORT_CURRENCIES:
        value = normalized.get(currency)
        if value is None:
            continue
        suffix = " (derived)" if currency == "AZN" else ""
        lines.append(f"- {currency}: {value}{suffix}")

    lines.append("")
    lines.append(
        "Source: Frankfurter API (frankfurter.app). "
        "AZN is derived via EUR→USD × USD→AZN peg."
    )
    lines.append(f"USD→AZN peg: {service.usd_azn_peg}")

    return "\n".join(lines)


async def send_telegram_message(message: str) -> None:
    bot_token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")

    bot = telegram.Bot(token=bot_token)

    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except TypeError:
        # sync fallback
        await asyncio.to_thread(bot.send_message, chat_id, message)


# ------------------------------
# Entrypoint
# ------------------------------
async def _main_async():
    service = FXService(
        api_url=FRANKFURTER_API_URL,
        base_currency=BASE_CURRENCY,
        api_currencies=API_CURRENCIES,
        usd_azn_peg=USD_AZN_PEG,
    )

    try:
        rates_data = service.get_fx_rates()
        message = format_message(rates_data, service)
        print(message)
        await send_telegram_message(message)
        print("✅ Notification sent successfully")
    except (requests.exceptions.RequestException, FXServiceError, RuntimeError) as e:
        print(f"❌ Error: {e}")


def main():
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
