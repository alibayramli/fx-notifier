import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests
import telegram

# Allow imports from project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from fx_bot import (
    ConfigError,
    FXService,
    FXServiceError,
    format_message,
    get_fx_rates,
    send_telegram_message,
)


@pytest.fixture
def fx_env(monkeypatch):
    monkeypatch.setenv("FRANKFURTER_API_URL", "https://api.frankfurter.app/latest")
    monkeypatch.setenv("BASE_CURRENCY", "EUR")
    monkeypatch.setenv("API_CURRENCIES", "USD,HUF")
    monkeypatch.setenv("USD_AZN_PEG", "1.7")
    monkeypatch.setenv("REPORT_CURRENCIES", "USD,HUF,AZN")


@patch("fx_bot.requests.get")
def test_get_fx_rates_success(mock_get, fx_env):
    mock_response = Mock()
    mock_response.json.return_value = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2024-07-26",
        "rates": {"USD": 1.088, "HUF": 393.4},
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    rates_data = get_fx_rates()

    assert rates_data["base"] == "EUR"
    assert rates_data["rates"]["USD"] == 1.088


@patch("fx_bot.requests.get")
def test_get_fx_rates_retries_request_errors(mock_get, fx_env):
    mock_response = Mock()
    mock_response.json.return_value = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2024-07-26",
        "rates": {"USD": 1.088, "HUF": 393.4},
    }
    mock_response.raise_for_status.return_value = None
    mock_get.side_effect = [requests.RequestException("temp"), mock_response]

    service = FXService.from_env()
    rates_data = service.get_fx_rates(retries=2, backoff_seconds=0)

    assert rates_data["rates"]["USD"] == 1.088
    assert mock_get.call_count == 2


@patch("fx_bot.requests.get")
def test_get_fx_rates_missing_rates_field_raises(mock_get, fx_env):
    mock_response = Mock()
    mock_response.json.return_value = {"amount": 1.0, "base": "EUR", "date": "2024-07-26"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    service = FXService.from_env()
    with pytest.raises(FXServiceError, match="missing 'rates'"):
        service.get_fx_rates()


def test_from_env_invalid_peg_raises_config_error(monkeypatch, fx_env):
    monkeypatch.setenv("USD_AZN_PEG", "not-a-number")

    with pytest.raises(ConfigError, match="USD_AZN_PEG must be a valid number"):
        FXService.from_env()


def test_normalize_rates_invalid_value_raises(fx_env):
    service = FXService.from_env()
    rates_data = {"rates": {"USD": "bad-value", "HUF": 393.4}}

    with pytest.raises(FXServiceError, match="Invalid rate for USD"):
        service.normalize_rates(rates_data, ("USD", "AZN"))


def test_format_message(fx_env):
    rates_data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2024-07-26",
        "rates": {
            "USD": 1.088,
            "HUF": 393.4,
            # AZN intentionally omitted - it is derived
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
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    async def runner():
        with pytest.raises(ConfigError):
            await send_telegram_message("Test message")

    asyncio.run(runner())


@patch("fx_bot.telegram.Bot")
def test_send_telegram_message_retries_on_telegram_error(mock_bot_cls, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

    mock_bot = Mock()
    mock_bot.send_message = AsyncMock(
        side_effect=[telegram.error.TimedOut("timeout"), None]
    )
    mock_bot_cls.return_value = mock_bot

    async def runner():
        await send_telegram_message("hello", retries=2, backoff_seconds=0)

    asyncio.run(runner())
    assert mock_bot.send_message.call_count == 2
