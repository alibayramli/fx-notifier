import types

import fx_bot


def test_cli_env_override(monkeypatch):
    # env values should be used when CLI doesn't override
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "envtoken")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "envchat")
    monkeypatch.setattr(fx_bot, "fetch_rates", lambda pairs: {"EUR/USD": 1.1})

    instances = []

    class DummyBot:
        def __init__(self, token):
            instances.append(self)
            self.token = token
            self.sent = []

        def send_message(self, chat_id, message):
            self.sent.append((chat_id, message))

    monkeypatch.setattr(fx_bot, "telebot", types.SimpleNamespace(TeleBot=DummyBot))

    fx_bot.run(fx_bot.parse_args(["--timezone", "UTC"]))

    assert instances, "TeleBot instance not created"
    assert instances[0].token == "envtoken"
    assert instances[0].sent[0][0] == "envchat"


def test_cli_overrides(monkeypatch):
    # CLI token/chat override env vars
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(fx_bot, "fetch_rates", lambda pairs: {"EUR/USD": 1.1})

    instances = []

    class DummyBot:
        def __init__(self, token):
            instances.append(self)
            self.token = token
            self.sent = []

        def send_message(self, chat_id, message):
            self.sent.append((chat_id, message))

    monkeypatch.setattr(fx_bot, "telebot", types.SimpleNamespace(TeleBot=DummyBot))

    fx_bot.run(
        fx_bot.parse_args(
            ["--token", "cli-token", "--chat-id", "cli-chat", "--timezone", "UTC"]
        )
    )

    assert instances, "TeleBot instance not created"
    assert instances[0].token == "cli-token"
    assert instances[0].sent[0][0] == "cli-chat"


def test_cli_dry_run(monkeypatch):
    # When --dry-run is used, no TeleBot instance should be created
    monkeypatch.setattr(fx_bot, "fetch_rates", lambda pairs: {"EUR/USD": 1.1})

    instances = []

    class DummyBot:
        def __init__(self, token):
            instances.append(self)

        def send_message(self, chat_id, message):
            pass

    monkeypatch.setattr(fx_bot, "telebot", types.SimpleNamespace(TeleBot=DummyBot))

    fx_bot.run(fx_bot.parse_args(["--dry-run", "--timezone", "UTC"]))

    assert not instances, "TeleBot should not be instantiated in dry-run mode"
