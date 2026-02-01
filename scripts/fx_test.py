#!/usr/bin/env python3
"""Diagnostic tool to query the FX provider directly.

Usage examples:
  EXCHANGERATE_ACCESS_KEY=KEY python scripts/fx_test.py --base EUR --symbols USD,AZN
  python scripts/fx_test.py --pairs EUR/USD,USD/HUF

This prints the HTTP status and the parsed JSON response so you can see provider error details.
"""
from __future__ import annotations

import argparse
import os
import sys
import requests
from typing import List

DEFAULT_API = os.environ.get(
    "EXCHANGE_API_URL", "https://api.exchangeratesapi.io/v1/latest"
)


def call_api(url: str, params: dict):
    try:
        r = requests.get(url, params=params, timeout=10)
    except Exception as e:
        print("Request failed:", e)
        return None, None
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


def parse_pairs(pairs: List[str]):
    # Build params grouped by base (same logic as fetch_rates)
    grouped = {}
    for p in pairs:
        p = p.strip().upper()
        if "/" not in p:
            continue
        base, quote = p.split("/", 1)
        grouped.setdefault(base.strip(), []).append(quote.strip())
    return grouped


def main(argv=None):
    p = argparse.ArgumentParser(description="FX provider diagnostic")
    p.add_argument("--base", help="Base currency, e.g. EUR")
    p.add_argument("--symbols", help="Comma-separated symbols like USD,AZN")
    p.add_argument("--pairs", help="Comma-separated pairs like EUR/USD,USD/HUF")
    p.add_argument("--url", help="Override API URL", default=DEFAULT_API)
    args = p.parse_args(argv)

    access_key = os.environ.get("EXCHANGERATE_ACCESS_KEY") or os.environ.get(
        "EXCHANGE_ACCESS_KEY"
    )

    pairs = []
    if args.pairs:
        pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]

    if args.base and args.symbols:
        pairs = [
            f"{args.base}/{s.strip()}" for s in args.symbols.split(",") if s.strip()
        ]

    if not pairs:
        print("No pairs supplied. Use --pairs or --base/--symbols")
        sys.exit(2)

    grouped = parse_pairs(pairs)

    overall_ok = True
    for base, quotes in grouped.items():
        params = {"base": base, "symbols": ",".join(quotes)}
        if access_key:
            params["access_key"] = access_key
        print("Requesting:", args.url, "params:", params)
        status, body = call_api(args.url, params)
        print("HTTP status:", status)
        print("Body:")
        print(body)
        if (
            status is None
            or (isinstance(body, dict) and body.get("success") is False)
            or (isinstance(status, int) and status >= 400)
        ):
            overall_ok = False
    if not overall_ok:
        print(
            "Provider reported errors — check EXCHANGERATE_ACCESS_KEY and EXCHANGE_API_URL (or provider docs)"
        )
        sys.exit(1)
    print("Provider returned rates successfully.")


if __name__ == "__main__":
    main()
