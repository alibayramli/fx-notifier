from unittest.mock import Mock, patch

import pytest
import requests

from fx_notifier import get_fx_rates
from fx_notifier.domain import ConfigError, FXServiceError
from fx_notifier.services import FXService


@patch("fx_notifier.infrastructure.frankfurter.requests.get")
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


@patch("fx_notifier.infrastructure.frankfurter.requests.get")
def test_get_fx_rates_retries_request_errors(mock_get, fx_env):
    mock_response = Mock()
    mock_response.json.return_value = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2024-07-26",
        "rates": {"USD": 1.088, "HUF": 393.4},
    }
    mock_response.raise_for_status.return_value = None
    mock_get.side_effect = [requests.ConnectionError("temp"), mock_response]

    service = FXService.from_env()
    rates_data = service.get_fx_rates(retries=2, backoff_seconds=0)

    assert rates_data["rates"]["USD"] == 1.088
    assert mock_get.call_count == 2


@patch("fx_notifier.infrastructure.frankfurter.requests.get")
def test_get_previous_rates_return_latest_prior_values(mock_get, fx_env):
    mock_response = Mock()
    mock_response.json.return_value = {
        "amount": 1.0,
        "base": "EUR",
        "start_date": "2024-07-19",
        "end_date": "2024-07-26",
        "rates": {
            "2024-07-24": {"USD": 1.084, "HUF": 392.1},
            "2024-07-25": {"USD": 1.085, "HUF": 392.8},
            "2024-07-26": {"USD": 1.088},
        },
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    service = FXService.from_env()

    previous_rates = service.get_previous_rates(
        ("USD", "HUF", "AZN"), "2024-07-26", backoff_seconds=0
    )

    assert previous_rates == {"USD": 1.085, "HUF": 392.8}


@patch("fx_notifier.infrastructure.frankfurter.requests.get")
def test_get_fx_rates_missing_rates_field_raises(mock_get, fx_env):
    mock_response = Mock()
    mock_response.json.return_value = {"amount": 1.0, "base": "EUR", "date": "2024-07-26"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    service = FXService.from_env()
    with pytest.raises(FXServiceError, match="missing 'rates'"):
        service.get_fx_rates()


@patch("fx_notifier.infrastructure.frankfurter.requests.get")
def test_get_fx_rates_does_not_retry_non_transient_http_error(mock_get, fx_env):
    mock_response = Mock(status_code=400)
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        "bad request",
        response=mock_response,
    )
    mock_get.return_value = mock_response

    service = FXService.from_env()
    with pytest.raises(requests.HTTPError):
        service.get_fx_rates(retries=3, backoff_seconds=0)

    assert mock_get.call_count == 1


def test_from_env_invalid_peg_raises_config_error(monkeypatch, fx_env):
    monkeypatch.setenv("USD_AZN_PEG", "not-a-number")

    with pytest.raises(ConfigError, match="USD_AZN_PEG must be a valid number"):
        FXService.from_env()


def test_normalize_rates_invalid_value_raises(fx_env):
    service = FXService.from_env()
    rates_data = {"rates": {"USD": "bad-value", "HUF": 393.4}}

    with pytest.raises(FXServiceError, match="Invalid rate for USD"):
        service.normalize_rates(rates_data, ("USD", "AZN"))
