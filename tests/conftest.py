import pytest


@pytest.fixture
def fx_env(monkeypatch):
    monkeypatch.setenv("FRANKFURTER_API_URL", "https://api.frankfurter.app/latest")
    monkeypatch.setenv("BASE_CURRENCY", "EUR")
    monkeypatch.setenv("API_CURRENCIES", "USD,HUF")
    monkeypatch.setenv("USD_AZN_PEG", "1.7")
    monkeypatch.setenv("REPORT_CURRENCIES", "USD,HUF,AZN")
