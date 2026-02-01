#!/usr/bin/env python3
"""Quick diagnostic for Telegram API connectivity.

Usage:
  TELEGRAM_BOT_TOKEN=TOKEN python scripts/telegram_test.py --chat CHAT_ID --text "Hello"
Or pass token and chat as args.

Note: Ensure `EXCHANGERATE_ACCESS_KEY` is set in the environment when running `fx_bot.py` or related scripts that fetch FX rates.
"""
from __future__ import annotations

import argparse
import os
import sys
import requests

API_BASE = "https://api.telegram.org"


def call_bot_api(token: str, method: str, params: dict | None = None):
    url = f"{API_BASE}/bot{token}/{method}"
    try:
        r = requests.post(url, data=params or {}, timeout=10)
    except Exception as exc:
        print("Request failed:", exc)
        return None
    try:
        return r.json()
    except Exception:
        print("Non-JSON response, HTTP status", r.status_code)
        print(r.text[:400])
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description="Telegram API diagnostic")
    p.add_argument("--token", help="Bot token (or set TELEGRAM_BOT_TOKEN env)")
    p.add_argument("--chat", help="Chat id to send message to")
    p.add_argument("--text", default="FX Notifier test message", help="Message text")
    p.add_argument(
        "--list-updates",
        action="store_true",
        dest="list_updates",
        help="Fetch getUpdates and print response",
    )
    args = p.parse_args(argv)

    token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: bot token required (env or --token)")
        sys.exit(2)

    print("Checking getMe()...")
    gm = call_bot_api(token, "getMe")
    print(gm)
    if not gm or not gm.get("ok"):
        print(
            "getMe failed. Check token format: URL must be https://api.telegram.org/bot<token>/METHOD"
        )
        sys.exit(1)

    if args.list_updates:
        print("Fetching getUpdates() (last 100 updates)...")
        up = call_bot_api(token, "getUpdates", {"limit": 100})
        print(up)

    if args.chat:
        print("Sending test message to chat", args.chat)
        resp = call_bot_api(
            token, "sendMessage", {"chat_id": args.chat, "text": args.text}
        )
        print(resp)
        if not resp or not resp.get("ok"):
            print(
                "sendMessage failed. Error details above. Common causes: wrong chat_id, user hasn't started the bot, or bot blocked."
            )
            sys.exit(1)

    print(
        "Diagnostics complete. If getMe passed but sendMessage failed, check chat id and that the user started the bot."
    )


if __name__ == "__main__":
    main()
