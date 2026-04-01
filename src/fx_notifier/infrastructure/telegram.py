from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from datetime import timedelta

import telegram

from fx_notifier.config import TelegramSettings


@dataclass(frozen=True)
class TelegramNotifier:
    settings: TelegramSettings

    @classmethod
    def from_env(cls) -> TelegramNotifier:
        return cls(TelegramSettings.from_env())

    async def send_message(
        self,
        message: str,
        retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        bot = telegram.Bot(token=self.settings.bot_token)
        attempts = max(1, retries)

        for attempt in range(1, attempts + 1):
            try:
                send_result = bot.send_message(
                    chat_id=self.settings.chat_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                if inspect.isawaitable(send_result):
                    await send_result
                return
            except telegram.error.TelegramError as exc:
                if attempt >= attempts or not self._should_retry_error(exc):
                    raise

                delay = backoff_seconds * attempt
                if isinstance(exc, telegram.error.RetryAfter):
                    retry_after = exc.retry_after
                    if isinstance(retry_after, timedelta):
                        delay = max(delay, retry_after.total_seconds())
                    else:
                        delay = max(delay, float(retry_after))
                await asyncio.sleep(delay)

        raise telegram.error.TelegramError("Failed to send Telegram message")

    @staticmethod
    def _should_retry_error(exc: telegram.error.TelegramError) -> bool:
        if isinstance(exc, telegram.error.BadRequest):
            return False
        return isinstance(
            exc,
            (
                telegram.error.NetworkError,
                telegram.error.RetryAfter,
                telegram.error.TimedOut,
            ),
        )


async def send_telegram_message(
    message: str,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> None:
    notifier = TelegramNotifier.from_env()
    await notifier.send_message(
        message,
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
