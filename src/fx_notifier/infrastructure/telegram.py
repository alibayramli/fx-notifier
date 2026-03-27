from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass

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
        last_error: Exception | None = None

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
                last_error = exc

            if attempt < attempts:
                await asyncio.sleep(backoff_seconds * attempt)

        if last_error is not None:
            raise last_error


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
