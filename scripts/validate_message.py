#!/usr/bin/env python3
"""Simple validation script to ensure message structure looks correct."""
import re
import sys
import os

# Ensure project root is importable when running this script directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fx_bot import format_message

print("Deprecated: Use `pytest` instead to validate formatting and behavior.")
# Keep exit code 0 for backwards compatibility in CI where this used to run
sys.exit(0)
