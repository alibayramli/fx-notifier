import builtins
import json
import types

import pytest

import fx_bot


class DummyResp:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status
        self.text = json.dumps(json_data)

    def json(self):
        return self._json


def test_normalize_pairs():
    out = fx_bot._normalize_pairs(["eur/usd", " USD/huf ", "badformat"])
    assert ("EUR", "USD") in out
    assert ("USD", "HUF") in out
    assert len(out) == 2


def test_fetch_rates_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert url == fx_bot.API_URL
        base = params.get("base")
        symbols = params.get("symbols")
        if base == "EUR":
            return DummyResp({"rates": {"USD": 1.07, "AZN": 1.91}})
        if base == "USD":
            return DummyResp({"rates": {"HUF": 363.5}})
        return DummyResp({"rates": {}})

    monkeypatch.setattr(fx_bot.requests, "get", fake_get)
    pairs = ["EUR/USD", "EUR/AZN", "USD/HUF"]
    rates = fx_bot.fetch_rates(pairs)
    assert rates["EUR/USD"] == pytest.approx(1.07)
    assert rates["EUR/AZN"] == pytest.approx(1.91)
    assert rates["USD/HUF"] == pytest.approx(363.5)


def test_fetch_rates_api_error(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResp({"error": "bad"}, status=500)

    monkeypatch.setattr(fx_bot.requests, "get", fake_get)
    with pytest.raises(RuntimeError):
        fx_bot.fetch_rates(["EUR/USD"])


def test_format_message_empty():
    msg = fx_bot.format_message({}, tz="UTC")
    assert "No rates available" in msg


def test_format_message_contains_rates():
    rates = {"EUR/USD": 1.071234, "USD/HUF": 363.5123}
    msg = fx_bot.format_message(rates, tz="UTC")
    assert "EUR/USD" in msg and "USD/HUF" in msg
    assert "1.071234" in msg or "1.071234" in msg
