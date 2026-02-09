# fx-notifier

FX Notifier is a Python project that automates fetching foreign exchange rates from the Frankfurter API and sending them as daily notifications to a Telegram channel.

## Features

- Fetches FX rates for EUR/USD, EUR/HUF, and EUR/AZN.
- Sends daily notifications to a Telegram channel.
- Scheduled to run on weekdays via GitHub Actions.
- Includes unit tests with pytest.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/fx-notifier.git
    cd fx-notifier
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows, use `env\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    - Create a `.env` file by copying the `env.template`:
      ```bash
      cp env.template .env
      ```
    - Edit the `.env` file and add your Telegram bot token and chat ID:
      ```
      TELEGRAM_BOT_TOKEN=your_bot_token
      TELEGRAM_CHAT_ID=your_chat_id
      ```

4.  **To send a test notification:**
    ```bash
    python fx_bot.py
    ```

## GitHub Actions

The project is configured to run automatically on weekdays. For this to work, you need to add the `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as secrets to your GitHub repository.

1.  Go to your repository's **Settings** > **Secrets and variables** > **Actions**.
2.  Click **New repository secret** for each secret:
    - `TELEGRAM_BOT_TOKEN`
    - `TELEGRAM_CHAT_ID`

The workflow is defined in `.github/workflows/fx-notifier.yml`.
