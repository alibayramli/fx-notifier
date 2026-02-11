import os
import sys
import asyncio

import pytest
from unittest.mock import patch, Mock

# Allow imports from project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from fx_bot import get_fx_rates, format_message, send_telegram_message


# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def fx_env(monkeypatch):
    """
    Provides all required FXService environment variables for testing.
    """
    monkeypatch.setenv("FRANKFURTER_API_URL", "https://api.frankfurter.app/latest")
    monkeypatch.setenv("BASE_CURRENCY", "EUR")
    monkeypatch.setenv("API_CURRENCIES", "USD,HUF")
    monkeypatch.setenv("USD_AZN_PEG", "1.7")
    monkeypatch.setenv("REPORT_CURRENCIES", "USD,HUF,AZN")


# -----------------------------
# Tests
# -----------------------------
@patch("fx_bot.requests.get")
def test_get_fx_rates_success(mock_get, fx_env):
    """
    get_fx_rates returns expected data on successful API call.
    """
    mock_response = Mock()
    mock_response.json.return_value = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2024-07-26",
        "rates": {
            "USD": 1.088,
            "HUF": 393.4,
        },
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    rates_data = get_fx_rates()

    assert rates_data["base"] == "EUR"
    assert rates_data["rates"]["USD"] == 1.088


def test_format_message(fx_env):
    """
    format_message outputs a correctly formatted message and marks AZN as derived.
    """
    rates_data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2024-07-26",
        "rates": {
            "USD": 1.088,
            "HUF": 393.4,
            # AZN intentionally omitted — it is derived
        },
    }

    message = format_message(rates_data)

    derived_azn = round(1.088 * 1.7, 6)

    expected = (
        "FX Rates for 2024-07-26 (Base: EUR):\n"
        "- USD: 1.088\n"
        "- HUF: 393.4\n"
        f"- AZN: {derived_azn} (derived)\n\n"
        "Source: Frankfurter API (frankfurter.app). "
        "AZN is derived via EUR->USD * USD->AZN peg.\n"
        "Configured USD->AZN peg: 1.7"
    )

    assert message == expected


def test_send_telegram_message_missing_env_vars(monkeypatch):
    """
    send_telegram_message should fail fast when TELEGRAM_* env vars are missing.
    """
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    async def runner():
        import pytest

        with pytest.raises(RuntimeError):
            await send_telegram_message("Test message")

    asyncio.run(runner())
