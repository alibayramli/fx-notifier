# fx-notifier

FX Notifier is a small Python utility that fetches foreign-exchange rates from the Frankfurter API and sends daily notifications to a Telegram channel.

## Features

- Fetches FX rates (e.g. `EUR/USD`, `EUR/HUF`) from the Frankfurter API
- Derives `EUR/AZN` using a fixed USD→AZN peg (EUR/AZN = EUR/USD × USD/AZN)
- Sends daily notifications to a Telegram channel
- Scheduled to run on weekdays via GitHub Actions
- Includes unit tests with `pytest`
- Uses environment-based configuration

## Requirements

- Python 3.8+
- The packages listed in `requirements.txt`

## Installation

1. Clone the repository:

```bash
git clone https://github.com/alibayramli/fx-notifier.git
cd fx-notifier
```

2. Create and activate a virtual environment, then install dependencies:

Unix / macOS (bash / zsh)

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell / CMD):

```powershell
python -m venv env
env\Scripts\Activate.ps1
pip install -r requirements.txt
```

Note: If script execution is blocked, run this once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Command Prompt (CMD):

```
python -m venv env
env\Scripts\activate.bat
pip install -r requirements.txt
```

After activation, your terminal prompt should be prefixed with:

```text
(env)
```

## Configuration

Copy the environment template and fill in the values:

```bash
cp env.template .env    # On Windows: copy env.template .env
```

Example `.env` (fill with your values):

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
FRANKFURTER_API_URL=https://api.frankfurter.app/latest
BASE_CURRENCY=EUR
API_CURRENCIES=USD,HUF
REPORT_CURRENCIES=USD,HUF,AZN
USD_AZN_PEG=1.7
```

Notes:

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are required for sending messages
- `API_CURRENCIES` should list comma-separated currencies to fetch from the API
- `REPORT_CURRENCIES` lists currencies to include in the report (including any derived ones)

## Usage

Send a manual/test notification:

```bash
python fx_bot.py
```

Run the test suite:

```bash
pytest
```

## GitHub Actions (CI / Scheduled Runs)

The project includes a GitHub Actions workflow that runs on weekdays. To enable it, add the following repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Add them at: Settings → Secrets and variables → Actions

The workflow definition is located at `.github/workflows/fx-notifier.yml`.

## Contributing

Contributions, bug reports and feature requests are welcome. Please open an issue or a pull request.

## License

MIT — use it, fork it, improve it
