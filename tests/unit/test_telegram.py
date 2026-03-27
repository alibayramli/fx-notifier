import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
import telegram

from fx_notifier.domain import ConfigError
from fx_notifier.infrastructure import send_telegram_message


def test_send_telegram_message_missing_env_vars(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    async def runner():
        with pytest.raises(ConfigError):
            await send_telegram_message("Test message")

    asyncio.run(runner())


@patch("fx_notifier.infrastructure.telegram.telegram.Bot")
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
    mock_bot.send_message.assert_any_call(
        chat_id="chat",
        text="hello",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
