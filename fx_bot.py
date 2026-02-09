import os
import asyncio

import requests
import telegram
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
FRANKFURTER_API_URL = "https://api.frankfurter.app/latest"
CURRENCIES = ["USD", "HUF", "AZN"]
BASE_CURRENCY = "EUR"


def get_fx_rates():
    """Fetches FX rates from the Frankfurter API."""
    params = {
        "to": ",".join(CURRENCIES),
        "from": BASE_CURRENCY,
    }

    response = requests.get(
        FRANKFURTER_API_URL,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def format_message(rates_data):
    """Formats the FX rates into a message."""
    rates = rates_data.get("rates", {})
    date = rates_data.get("date", "N/A")

    lines = [f"FX Rates for {date} (Base: {BASE_CURRENCY}):"]
    for currency in CURRENCIES:
        if currency in rates:
            lines.append(f"- {currency}: {rates[currency]}")

    return "\n".join(lines)


async def send_telegram_message(message: str) -> None:
    """Sends a message to the Telegram channel."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not all([bot_token, chat_id]):
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables are not set."
        )

    bot = telegram.Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)


async def main():
    """Main function to fetch and send FX rates."""
    try:
        rates_data = get_fx_rates()
        message = format_message(rates_data)
        await send_telegram_message(message)
        print("✅ Notification sent successfully")
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
