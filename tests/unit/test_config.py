import pytest

from fx_notifier.config import FXSettings
from fx_notifier.domain import ConfigError


def test_fx_settings_require_usd_when_azn_is_reported(monkeypatch, fx_env):
    monkeypatch.setenv("API_CURRENCIES", "HUF")

    with pytest.raises(ConfigError, match="API_CURRENCIES must include USD"):
        FXSettings.from_env()


def test_fx_settings_require_non_empty_report_currencies(monkeypatch, fx_env):
    monkeypatch.setenv("REPORT_CURRENCIES", "")

    with pytest.raises(ConfigError, match="REPORT_CURRENCIES must include at least one currency"):
        FXSettings.from_env()


def test_fx_settings_reject_unsupported_report_currencies(monkeypatch, fx_env):
    monkeypatch.setenv("REPORT_CURRENCIES", "USD,GBP")

    with pytest.raises(ConfigError, match="unsupported currencies: GBP"):
        FXSettings.from_env()


def test_fx_settings_normalize_currency_codes(monkeypatch, fx_env):
    monkeypatch.setenv("BASE_CURRENCY", " eur ")
    monkeypatch.setenv("API_CURRENCIES", " usd , huf , usd ")
    monkeypatch.setenv("REPORT_CURRENCIES", " usd , azn ")

    settings = FXSettings.from_env()

    assert settings.base_currency == "EUR"
    assert settings.api_currencies == ("USD", "HUF")
    assert settings.report_currencies == ("USD", "AZN")
