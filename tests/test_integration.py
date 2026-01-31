import re
import types

import fx_bot


def test_telegram_integration(monkeypatch):
    instances = []

    class DummyBot:
        def __init__(self, token):
            instances.append(self)
            self.token = token
            self.sent = []

        def send_message(self, chat_id, message):
            self.sent.append((chat_id, message))

    monkeypatch.setattr(fx_bot, "telebot", types.SimpleNamespace(TeleBot=DummyBot))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat123")
    monkeypatch.setattr(
        fx_bot, "fetch_rates", lambda pairs: {"EUR/USD": 1.2345, "USD/HUF": 363.5}
    )

    # Run notifier (will use the dummy bot)
    fx_bot.run(fx_bot.parse_args(["--timezone", "UTC"]))

    assert instances, "No TeleBot instances created"
    sent = instances[0].sent
    assert sent, "No messages sent"
    chat_id, message = sent[0]
    assert chat_id == "chat123"
    assert "FX Rates" in message
    assert "EUR/USD" in message and "USD/HUF" in message
    assert re.search(r"\d{4}-\d{2}-\d{2}", message)
