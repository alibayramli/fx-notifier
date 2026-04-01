# fx-notifier

FX Notifier is a packaged Python application that fetches foreign-exchange rates from the Frankfurter API and sends formatted Telegram notifications.

## Features

- `src/` layout with clear boundaries for config, domain errors, infrastructure adapters, services, and app workflows
- Single source of truth for packaging, test, lint, and type-check configuration in `pyproject.toml`
- Installable CLI via `fx-notifier`
- Retries transient API and Telegram failures with backoff
- Scheduled weekday delivery through GitHub Actions
- Unit tests plus lint and static type checks

## Repository Layout

```text
fx-notifier/
|-- pyproject.toml
|-- src/
|   `-- fx_notifier/
|       |-- __main__.py       # CLI/module entrypoint
|       |-- config.py         # Environment parsing and typed settings
|       |-- app/
|       |   `-- workflows.py  # Application orchestration
|       |-- domain/
|       |   `-- errors.py     # Domain and configuration errors
|       |-- infrastructure/
|       |   |-- frankfurter.py
|       |   `-- telegram.py
|       `-- services/
|           |-- fx.py
|           `-- reporting.py
|-- scripts/
|   |-- run_checks.sh
|   `-- run_checks.ps1
`-- tests/
    |-- conftest.py
    `-- unit/
```

## Requirements

- Python 3.10+

## Installation

For development:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
pre-commit install
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
pre-commit install
```

For runtime-only installation:

```bash
python -m pip install .
```

## Configuration

Copy the environment template and fill in the values:

```bash
cp env.template .env
```

Example `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
FRANKFURTER_API_URL=https://api.frankfurter.app/latest
BASE_CURRENCY=EUR
API_CURRENCIES=USD,HUF
REPORT_CURRENCIES=USD,HUF,AZN
USD_AZN_PEG=1.7
```

## Usage

Run the installed CLI:

```bash
fx-notifier
```

Module entrypoint also works after installation:

```bash
python -m fx_notifier
```

Run the quality gate locally:

```bash
bash scripts/run_checks.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_checks.ps1
```

## Formatting

- Python formatting and import cleanup are enforced by `ruff`.
- `.editorconfig` keeps line endings, final newlines, and trailing whitespace consistent across editors.
- `.vscode/settings.json` enables format-on-save for Python with the Ruff extension.
- `.pre-commit-config.yaml` runs formatting fixes before each commit after `pre-commit install`.

## GitHub Actions

The workflow runs the quality gate on pushes and pull requests, then sends notifications only for scheduled and manual runs.

Required repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## License

MIT
