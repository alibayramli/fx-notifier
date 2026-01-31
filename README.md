# fx-notifier

FX Notifier is a Python project that automates fetching foreign exchange (FX) rates and sending them as daily notifications to messaging platforms.

## Features ✅

- Fetch FX rates from exchangerate.host
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
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
python fx_bot.py
```

Use `DRY_RUN=1` to print the message without sending it.

## CLI Usage

You can use the built-in CLI to control runs without exporting environment variables. Run `python fx_bot.py --help` for full options.

Examples:

```bash
# Dry-run, print message and don't send
python fx_bot.py --dry-run

# Specify pairs and timezone
python fx_bot.py --pairs "EUR/USD,USD/HUF" --timezone UTC --dry-run

# Override Telegram credentials on the command line
python fx_bot.py --token "<your-token>" --chat-id "<your-chat-id>"
```

You can also use the included `Makefile`:

```bash
make install    # install dependencies
make test       # run the test-suite
make run-dry    # run without sending
```

Use the provided `env.template` as a sample for environment variables or GitHub secrets.

## Validation script

There's a small validation script that CI runs to ensure the formatted message looks correct:

```bash
python scripts/validate_message.py
```

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
