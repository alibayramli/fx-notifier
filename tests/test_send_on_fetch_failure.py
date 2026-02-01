import fx_bot


def test_send_on_fetch_failure(monkeypatch):
    # Simulate fetch raising an error
    def bad_fetch(pairs):
        raise RuntimeError("API error: invalid_api_function")

    monkeypatch.setattr(fx_bot, "fetch_rates", bad_fetch)

    called = {}

    def fake_call(token, method, params):
        called["called"] = True
        # message text should include 'Could not fetch' and a brief actionable hint
        assert "Could not fetch FX rates" in params["text"]
        assert "EXCHANGERATE_ACCESS_KEY" in params["text"]
        # Ensure we don't leak raw provider JSON into the message
        assert "{" not in params["text"] and '"success"' not in params["text"]
        return {"ok": True}

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.setattr(fx_bot, "call_telegram_api", fake_call)

    # Run without raising — should call our fake_call
    fx_bot.run(fx_bot.parse_args(["--timezone", "UTC"]))
    assert called.get("called")
