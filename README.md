# fx-notifier

FX Notifier is a Python project that automates fetching foreign exchange (FX) rates and sending them as daily notifications to messaging platforms.

## Features ✅

- Fetch FX rates from exchangeratesapi.io
- Send daily notifications to Telegram (extensible to Slack/Discord/Email)
- Scheduled run via GitHub Actions (weekday mornings)
- Unit tests with pytest

## Quickstart 🔧

1. Add secrets to your repository: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
2. Optionally set `PAIRS` (comma-separated, default: `EUR/USD,EUR/AZN,USD/HUF`) and `TIMEZONE` (default: `Asia/Baku`).
3. The GitHub Actions workflow runs on weekdays at 09:00 Baku time (UTC+4) by default.

## Local run

Set env vars and run:

```bash
pip install -r requirements.txt
export EXCHANGERATE_ACCESS_KEY=YOUR_ACCESS_KEY
export TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
export TELEGRAM_CHAT_ID=YOUR_CHAT_ID
python fx_bot.py
```

Use `DRY_RUN=1` to print the message without sending it.

## .env support

Place your keys in a `.env` file in the project root (format: `KEY=value`) and the script will load them automatically when run locally. This lets you run `python fx_bot.py` without exporting environment variables manually.

## CLI Usage

You can use the built-in CLI to control runs without exporting environment variables. Run `python fx_bot.py --help` for full options.

Examples:

```bash
# Dry-run, print message and don't send
python fx_bot.py --dry-run

# Specify pairs and timezone
python fx_bot.py --pairs "EUR/USD,USD/HUF" --timezone UTC --dry-run

# Override Telegram credentials on the command line
python fx_bot.py --token TOKEN --chat-id CHAT_ID
```

## Test send (handy for diagnostics)

If you want to verify that sending messages works end-to-end without hooking into CI, use the `--test-send` flag. It performs a single HTTP API call and prints the raw JSON response.

```bash
# Use environment secrets
EXCHANGERATE_ACCESS_KEY=YOUR_ACCESS_KEY TELEGRAM_BOT_TOKEN=TOKEN TELEGRAM_CHAT_ID=CHAT_ID python fx_bot.py --test-send

# Or pass token/chat on CLI
# This form is intended for `--test-send` (no access key required).
python fx_bot.py --test-send --token TOKEN --chat-id CHAT_ID

Note: Full runs require `EXCHANGERATE_ACCESS_KEY` to be set in the environment. Optionally, set `EXCHANGE_API_URL` to point at a different FX provider or a self-hosted endpoint. When running locally, python-dotenv will be used if installed to load a `.env` file.
```

You can also use the included `Makefile`:

```bash
make install    # install dependencies
make test       # run the test-suite
make run-dry    # run without sending
```

Use the provided `env.template` as a sample for environment variables or GitHub secrets.

## Testing ✅

Run tests with:

```bash
pytest
```

## Extensibility 💡

- The messaging logic is isolated (`TelegramSender`) for easy extension.
- Add providers (Slack, Discord, Email) by implementing a small `send(message)` wrapper.

---

Contributions welcome! Open issues or pull requests on GitHub.
