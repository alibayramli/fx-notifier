#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.txt
python -m pytest -q tests
python -m py_compile fx_bot.py
