# GD Demon List Bot

A Telegram bot for Geometry Dash Demonlist fans. The bot uses the
[Pointercrate API](https://pointercrate.com/documentation/) for Demonlist data
and the [GDBrowser API](https://gdbrowser.com/api) for Geometry Dash player
profiles.

## Features

- Show the current Pointercrate Top 10 demons.
- Search Geometry Dash player profiles by nickname.
- Generate a daily Demonlist challenge.
- Let users complete the daily challenge once per day for points.
- Track user point balances in SQLite.
- Notify subscribers when listed demons are added, removed, or moved.
- Provide a Telegram reply keyboard for common actions.

## Commands

| Command | Description |
| --- | --- |
| `/start` | Open the main bot panel. |
| `/top10_levels` | Show the current Top 10 demons from Pointercrate. |
| `/profile <nickname>` | Search for a Geometry Dash player profile. |
| `/daily` | Show today's daily challenge. |
| `/complete` | Mark today's daily challenge as completed and earn 1 point. |
| `/points` | Show your current point balance. |
| `/notifications_on` | Subscribe to Demonlist change notifications. |
| `/notifications_off` | Unsubscribe from Demonlist change notifications. |
| `/notifications` | Show your notification subscription status. |
| `/cancel` | Cancel an interactive profile search. |

## Requirements

- Python 3.10 or newer
- A Telegram bot token from [BotFather](https://t.me/BotFather)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)

Python packages are pinned in `requirements.txt`.

## Setup

1. Clone the project and enter the directory.

   ```bash
   git clone <your-repo-url>
   cd GDbot
   ```

2. Create and activate a virtual environment.

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS or Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file from the example file.

   ```bash
   cp .env.example .env
   ```

   On Windows PowerShell, you can use:

   ```powershell
   Copy-Item .env.example .env
   ```

   Then fill in your real Telegram credentials:

   ```env
   TELEGRAM_API_ID=123456
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_BOT_TOKEN=your_bot_token
   ```

   `.env` is ignored by Git, so your local secrets stay out of version control.

   You can also set the same values directly as environment variables instead
   of using a `.env` file.

   Windows PowerShell:

   ```powershell
   $env:TELEGRAM_API_ID = "123456"
   $env:TELEGRAM_API_HASH = "your_api_hash"
   $env:TELEGRAM_BOT_TOKEN = "your_bot_token"
   ```

   macOS or Linux:

   ```bash
   export TELEGRAM_API_ID="123456"
   export TELEGRAM_API_HASH="your_api_hash"
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   ```

   Configure the same variables in your hosting provider for deployment.

5. Run the bot.

   ```bash
   python main.py
   ```

On startup, the app creates the required SQLite tables automatically in
`gd_bot.db`.

## Deployment

The project includes a `Procfile` for platforms that support worker processes:

```Procfile
worker: python main.py
```

Make sure the deployment environment provides `TELEGRAM_API_ID`,
`TELEGRAM_API_HASH`, and `TELEGRAM_BOT_TOKEN` before starting the worker. For
local development, the bot also loads these values from a `.env` file in the
project root.

## Project Structure

| File | Purpose |
| --- | --- |
| `main.py` | Environment variable loading, Pyrogram bot setup, command handlers, daily challenge flow, and Demonlist monitoring loop. |
| `api.py` | Async API helpers for Pointercrate and GDBrowser. |
| `database.py` | SQLite tables and persistence helpers for users, completions, daily challenges, notifications, and snapshots. |
| `keyboards.py` | Telegram reply keyboard buttons and layout. |
| `drafts.py` | Older draft code for static demon photo responses. |
| `.env.example` | Template for local environment configuration. |
| `requirements.txt` | Pinned Python dependencies. |
| `Procfile` | Worker entrypoint for deployment platforms. |
| `*.png` | Image assets used by older draft/static bot responses. |

## Data Files

The bot may create or update these local runtime files:

- `gd_bot.db` - SQLite database for user points, daily challenges, completions,
  notification subscriptions, and Demonlist snapshots.
- `DemonList.session` - Pyrogram session file.
- `DemonList.session-journal` - SQLite journal file for the session.

These files can contain local runtime state and should usually stay out of
version control.

## How It Works

When the bot starts, it initializes database tables, starts the Pyrogram client,
and launches a background Demonlist monitor. The monitor checks Pointercrate
every 10 minutes, compares the latest listed demons with the saved snapshot, and
sends a message to subscribed users when it detects additions, removals, or
position changes.

Daily challenges are selected from the Pointercrate top 100. Each date gets one
stored challenge, and each Telegram user can complete that challenge once for 1
point.

## Security Notes

- Store Telegram API credentials and bot tokens in environment variables.
- Do not commit real Telegram API credentials or bot tokens.
- Rotate a token immediately if it has been shared publicly.
- Treat session and database files as private runtime data.
