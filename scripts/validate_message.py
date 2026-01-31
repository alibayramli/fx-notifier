#!/usr/bin/env python3
"""Simple validation script to ensure message structure looks correct."""
import re
import sys
import os

# Ensure project root is importable when running this script directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fx_bot import format_message

msg = format_message({"EUR/USD": 1.2345}, tz="UTC")
print(msg)
if (
    "FX Rates" not in msg
    or "EUR/USD" not in msg
    or not re.search(r"\d{4}-\d{2}-\d{2}", msg)
):
    print("Message validation failed", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
