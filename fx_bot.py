"""FX Notifier - fetch FX rates and send to Telegram

Usage: configure via environment variables:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- PAIRS (optional, comma-separated like "EUR/USD,USD/HUF")
- TIMEZONE (optional, default: Asia/Baku)
- DRY_RUN (optional, set to "1" to skip sending)
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Dict, Iterable, List, Tuple
from datetime import datetime, timezone
import argparse

import requests

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

try:
    import telebot
except Exception:
    telebot = None  # type: ignore

DEFAULT_PAIRS = ["EUR/USD", "EUR/AZN", "USD/HUF"]
API_URL = "https://api.exchangerate.host/latest"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _normalize_pairs(pairs: Iterable[str]) -> List[Tuple[str, str]]:
    out = []
    for p in pairs:
        p = p.strip().upper()
        if not p or "/" not in p:
            continue
        base, quote = p.split("/", 1)
        out.append((base.strip(), quote.strip()))
    return out


def fetch_rates(pairs: Iterable[str]) -> Dict[str, float]:
    """Fetch exchange rates for given pairs.

    Returns mapping like {'EUR/USD': 1.07, ...}
    Raises RuntimeError on failure.
    """
    pairs_list = _normalize_pairs(pairs)
    if not pairs_list:
        return {}

    # Group by base to minimize API calls
    grouped: Dict[str, List[str]] = {}
    for base, quote in pairs_list:
        grouped.setdefault(base, []).append(quote)

    results: Dict[str, float] = {}
    for base, quotes in grouped.items():
        params = {"base": base, "symbols": ",".join(quotes)}
        resp = requests.get(API_URL, params=params, timeout=10)
        if resp.status_code != 200:
            logger.error("Failed to fetch rates for base=%s: %s", base, resp.text)
            raise RuntimeError(f"API error (status {resp.status_code})")
        data = resp.json()
        rates = data.get("rates") or {}
        for q in quotes:
            rate = rates.get(q)
            if rate is None:
                logger.warning("Missing rate for %s/%s", base, q)
                continue
            results[f"{base}/{q}"] = float(rate)
    return results


def format_message(rates: Dict[str, float], tz: str = "Asia/Baku") -> str:
    # Use timezone-aware UTC datetime to avoid deprecation warnings
    now = datetime.now(timezone.utc)
    try:
        if ZoneInfo:
            local = now.astimezone(ZoneInfo(tz))
        else:
            local = now
    except Exception:
        local = now
    header = f"FX Rates — {local.strftime('%Y-%m-%d %H:%M %Z')}"
    lines = [header, ""]
    if not rates:
        lines.append("No rates available.")
    else:
        for pair in sorted(rates.keys()):
            lines.append(f"{pair}: {rates[pair]:.6f}")
    return "\n".join(lines)


class TelegramSender:
    def __init__(self, token: str, chat_id: str):
        if not token or not chat_id:
            raise ValueError("token and chat_id are required")
        if telebot is None:
            raise RuntimeError("pyTelegramBotAPI (telebot) is not installed")
        self.bot = telebot.TeleBot(token)
        self.chat_id = chat_id

    def send(self, message: str) -> None:
        try:
            self.bot.send_message(self.chat_id, message)
            logger.info("Message sent to Telegram chat %s", self.chat_id)
        except Exception as exc:  # pragma: no cover - network call
            logger.exception("Failed to send Telegram message: %s", exc)
            raise


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="FX Notifier")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Do not send messages, only print",
    )
    parser.add_argument(
        "--pairs", type=str, help="Comma-separated pairs like 'EUR/USD,USD/HUF'"
    )
    parser.add_argument(
        "--timezone", type=str, help="Timezone (IANA), default Asia/Baku"
    )
    parser.add_argument("--token", type=str, help="Telegram bot token (overrides env)")
    parser.add_argument(
        "--chat-id", type=str, dest="chat_id", help="Telegram chat id (overrides env)"
    )
    return parser.parse_args(argv)


def run(args=None):
    if args is None:
        args = parse_args()
    pairs_env = args.pairs or os.environ.get("PAIRS", ",".join(DEFAULT_PAIRS))
    pairs = [p.strip() for p in pairs_env.split(",") if p.strip()]
    timezone = args.timezone or os.environ.get("TIMEZONE", "Asia/Baku")
    dry = args.dry_run or os.environ.get("DRY_RUN", "0") in ("1", "true", "True")

    try:
        rates = fetch_rates(pairs)
    except Exception as exc:
        logger.error("Error fetching rates: %s", exc)
        raise

    message = format_message(rates, tz=timezone)
    print(message)

    if dry:
        logger.info("DRY_RUN set, not sending message")
        return

    token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = args.chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping send")
        return

    sender = TelegramSender(token=token, chat_id=chat)
    sender.send(message)


def main(argv=None):
    try:
        run(parse_args(argv))
    except SystemExit:
        raise
    except Exception:
        sys.exit(2)


if __name__ == "__main__":
    main()
