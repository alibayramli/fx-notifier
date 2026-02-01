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
API_URL = "https://api.exchangeratesapi.io/v1/latest"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_dotenv(path: str = ".env") -> None:
    """Load environment variables from a .env file.

    Prefer `python-dotenv` when installed; otherwise use a tiny local loader.
    Existing environment variables are not overwritten.
    """
    p = os.path.join(os.path.dirname(__file__), path)
    if not os.path.exists(p):
        return

    # Prefer python-dotenv when available
    try:
        from dotenv import load_dotenv as _pd_load  # type: ignore

        _pd_load(p, override=False)
        return
    except Exception:
        pass

    # Fallback local loader
    try:
        with open(p, "r", encoding="utf8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        logger.exception("Failed to load .env file: %s", p)


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
    access_key = os.environ.get("EXCHANGERATE_ACCESS_KEY") or os.environ.get(
        "EXCHANGE_ACCESS_KEY"
    )
    if not access_key:
        logger.error("EXCHANGERATE_ACCESS_KEY environment variable is required")
        raise RuntimeError("EXCHANGERATE_ACCESS_KEY environment variable is required")

    api_url = os.environ.get("EXCHANGE_API_URL", API_URL)

    # If the configured API URL is just a domain (no path), assume the 'latest' endpoint
    try:
        from urllib.parse import urlparse

        parsed = urlparse(api_url)
        if not parsed.path or parsed.path == "/":
            api_url = api_url.rstrip("/") + "/latest"
            logger.info("Normalized EXCHANGE_API_URL to %s", api_url)
    except Exception:
        pass

    for base, quotes in grouped.items():
        params = {"base": base, "symbols": ",".join(quotes), "access_key": access_key}
        logger.debug("Requesting %s with params %s", api_url, params)
        resp = requests.get(api_url, params=params, timeout=10)
        if resp.status_code != 200:
            # Try to parse JSON body for more context
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            logger.error("Failed to fetch rates for base=%s: %s", base, body)

            # Some providers (free tiers) do not support the `base` parameter and
            # return an 'invalid_api_function' error. In that case, retry without
            # the `base` param and request both the desired quotes and the base
            # itself so we can compute cross rates.
            should_retry = False
            if resp.status_code == 404:
                try:
                    if isinstance(body, dict):
                        err = body.get("error") or {}
                        if "invalid_api_function" in str(
                            err.get("type", "")
                        ) or "invalid_api_function" in str(err):
                            should_retry = True
                    else:
                        if "invalid_api_function" in str(body):
                            should_retry = True
                except Exception:
                    pass

            if should_retry:
                symbols = ",".join(sorted(set(quotes + [base])))
                params2 = {"symbols": symbols, "access_key": access_key}
                logger.info(
                    "Retrying without base param, requesting %s with params %s",
                    api_url,
                    params2,
                )
                resp2 = requests.get(api_url, params=params2, timeout=10)
                if resp2.status_code != 200:
                    try:
                        body2 = resp2.json()
                    except Exception:
                        body2 = resp2.text
                    logger.error("Fallback request failed for base=%s: %s", base, body2)
                    raise RuntimeError(
                        f"API error (status {resp2.status_code}): {body2}"
                    )
                data2 = resp2.json()
                rates2 = data2.get("rates") or {}
                provider_base = data2.get("base")
                for q in quotes:
                    if q == base:
                        results[f"{base}/{q}"] = 1.0
                        continue
                    r_q = rates2.get(q)
                    r_b = rates2.get(base)
                    if r_q is None or r_b is None:
                        logger.warning(
                            "Missing rate for %s/%s in fallback response", base, q
                        )
                        continue
                    # If provider's base matches requested base, use directly; otherwise
                    # compute cross-rate via the provider base (e.g., EUR)
                    if provider_base and provider_base.upper() == base:
                        results[f"{base}/{q}"] = float(r_q)
                    else:
                        results[f"{base}/{q}"] = float(r_q) / float(r_b)
                continue

            raise RuntimeError(f"API error (status {resp.status_code}): {body}")

        data = resp.json()
        # Some providers return {success: false, error: {...}} on failure
        if isinstance(data, dict) and data.get("success") is False:
            err = data.get("error") or {}
            logger.error("Exchange API returned error for base=%s: %s", base, err)
            raise RuntimeError(f"Exchange API error: {err}")
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


def call_telegram_api(token: str, method: str, params: dict | None = None):
    """Call Telegram HTTP API and return parsed JSON.

    Central helper used by tests and the `--test-send` flag.
    """
    url = f"https://api.telegram.org/bot{token}/{method}"
    r = requests.post(url, data=params or {}, timeout=10)
    try:
        return r.json()
    except Exception:
        r.raise_for_status()


class TelegramSender:
    def __init__(self, token: str, chat_id: str):
        if not token or not chat_id:
            raise ValueError("token and chat_id are required")
        self.token = token
        self.chat_id = chat_id
        self.bot = None
        if telebot is not None:
            try:
                # Some TeleBot implementations validate tokens eagerly;
                # if initialization fails, fall back to HTTP mode.
                self.bot = telebot.TeleBot(token)
            except Exception as exc:  # pragma: no cover - depends on telebot behavior
                logger.warning(
                    "telebot initialization failed, falling back to HTTP: %s", exc
                )
                self.bot = None

    def send(self, message: str) -> None:
        """Send via the installed library or fallback to HTTP API.

        This ensures clearer errors like `chat not found` are surfaced and
        provides a reliable fallback when `pyTelegramBotAPI` isn't working.
        """
        # Try library-based send first if available
        if self.bot is not None:
            try:
                self.bot.send_message(self.chat_id, message)
                logger.info(
                    "Message sent to Telegram chat %s (via telebot)", self.chat_id
                )
                return
            except Exception as exc:  # pragma: no cover - network behavior
                logger.warning(
                    "telebot send failed, will attempt HTTP fallback: %s", exc
                )

        # Fallback to HTTP API
        try:
            resp = call_telegram_api(
                self.token, "sendMessage", {"chat_id": self.chat_id, "text": message}
            )
        except Exception as exc:  # pragma: no cover - network behavior
            logger.exception("HTTP send failed: %s", exc)
            raise

        # Interpret the response
        if not (isinstance(resp, dict) and resp.get("ok")):
            err = resp or {}
            logger.error("Telegram API error: %s", err)
            code = err.get("error_code")
            desc = err.get("description")
            raise RuntimeError(f"Telegram API error (code={code}): {desc}")

        logger.info("Message sent to Telegram chat %s (via HTTP API)", self.chat_id)


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
    parser.add_argument(
        "--test-send",
        action="store_true",
        dest="test_send",
        help="Send a single test message via HTTP API and print the raw response",
    )
    return parser.parse_args(argv)


def run(args=None):
    # Load .env from project root (if present) so users can run without exporting
    load_dotenv()

    if args is None:
        args = parse_args()
    pairs_env = args.pairs or os.environ.get("PAIRS", ",".join(DEFAULT_PAIRS))
    pairs = [p.strip() for p in pairs_env.split(",") if p.strip()]
    tz = args.timezone or os.environ.get("TIMEZONE", "Asia/Baku")
    dry = args.dry_run or os.environ.get("DRY_RUN", "0") in ("1", "true", "True")

    # If user only wants to test-send, skip fetching FX rates to allow
    # quick diagnostics without requiring the exchange access key.
    if getattr(args, "test_send", False):
        ts = datetime.now(timezone.utc)
        try:
            if ZoneInfo:
                local = ts.astimezone(ZoneInfo(tz))
            else:
                local = ts
        except Exception:
            local = ts
        message = f"FX Notifier — Test send {local.strftime('%Y-%m-%d %H:%M %Z')}\n\nThis is a test message."
    else:
        try:
            rates = fetch_rates(pairs)
            message = format_message(rates, tz=tz)
        except Exception as exc:
            # Log full details, but send a concise, actionable message to users
            logger.error("Error fetching rates: %s", exc)
            ts = datetime.now(timezone.utc)
            try:
                if ZoneInfo:
                    local = ts.astimezone(ZoneInfo(tz))
                else:
                    local = ts
            except Exception:
                local = ts

            # Try to extract a short error hint (e.g., invalid_api_function or code)
            exc_text = str(exc)
            hint = None
            if "invalid_api_function" in exc_text:
                hint = "invalid_api_function"
            else:
                import re

                m = re.search(r"code\W*(\d{3})", exc_text)
                if m:
                    hint = f"code {m.group(1)}"

            hint_part = f" ({hint})" if hint else ""

            message = (
                f"FX Rates — Error — {local.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
                "Could not fetch FX rates due to a provider error."
                f"{hint_part} Please check `EXCHANGERATE_ACCESS_KEY` and `EXCHANGE_API_URL`."
                " See logs for details."
            )

    print(message)

    if dry:
        logger.info("DRY_RUN set, not sending message")
        return

    token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = args.chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping send")
        return

    # If requested, perform a single HTTP send for diagnostics and print the raw API response
    if getattr(args, "test_send", False):
        resp = call_telegram_api(
            token, "sendMessage", {"chat_id": chat, "text": message}
        )
        print(resp)
        if not (isinstance(resp, dict) and resp.get("ok")):
            raise RuntimeError(f"Telegram test send failed: {resp}")
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
