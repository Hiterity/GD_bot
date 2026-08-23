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
- Chat with an AI agent about Demonlist updates and Geometry Dash topics.
- Save AI chat history per Telegram user so conversations can continue later.
- Start AI chat from the `🤖 Start AI Chat` keyboard button.
- Let the AI agent use public web search for recent public information and
  source links.

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
| `/agent [message]` | Start or continue a saved AI conversation. |
| `/agent_stop` | Leave AI chat mode without clearing history. |
| `/agent_reset` | Clear your saved AI chat history. |
| `/cancel` | Cancel an interactive profile search. |

## Requirements

- Python 3.10 or newer
- A Telegram bot token from [BotFather](https://t.me/BotFather)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)
- A Mistral AI API key for the AI agent

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
   MISTRAL_API_KEY=replace_with_your_real_mistral_api_key
   MISTRAL_MODEL=mistral-large-latest
   ```

   `.env` is ignored by Git, so your local secrets stay out of version control.
   `MISTRAL_MODEL` is optional; the bot uses `mistral-large-latest` by default.

   You can also set the same values directly as environment variables instead
   of using a `.env` file.

   Windows PowerShell:

   ```powershell
   $env:TELEGRAM_API_ID = "123456"
   $env:TELEGRAM_API_HASH = "your_api_hash"
   $env:TELEGRAM_BOT_TOKEN = "your_bot_token"
   $env:MISTRAL_API_KEY = "your_mistral_api_key"
   $env:MISTRAL_MODEL = "mistral-large-latest"
   ```

   macOS or Linux:

   ```bash
   export TELEGRAM_API_ID="123456"
   export TELEGRAM_API_HASH="your_api_hash"
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export MISTRAL_API_KEY="your_mistral_api_key"
   export MISTRAL_MODEL="mistral-large-latest"
   ```

   Configure the same variables in your hosting provider for deployment.

5. Run the bot.

   ```bash
   python main.py
   ```

On startup, the app creates the required SQLite tables automatically in
`gd_bot.db`.

## Project Structure

| File | Purpose |
| --- | --- |
| `main.py` | Environment variable loading, Pyrogram bot setup, command handlers, daily challenge flow, and Demonlist monitoring loop. |
| `api.py` | Async API helpers for Pointercrate and GDBrowser. |
| `ai_agent.py` | Mistral-powered Geometry Dash AI agent logic. |
| `database.py` | SQLite tables and persistence helpers for users, completions, daily challenges, notifications, and snapshots. |
| `keyboards.py` | Telegram reply keyboard buttons and layout. |
| `drafts.py` | Older draft code for static demon photo responses. |
| `.env.example` | Template for local environment configuration. |
| `requirements.txt` | Pinned Python dependencies. |
| `*.png` | Image assets used by older draft/static bot responses. |

## Data Files

The bot may create or update these local runtime files:

- `gd_bot.db` - SQLite database for user points, daily challenges, completions,
  notification subscriptions, Demonlist snapshots, recent Demonlist update
  events, and saved AI chat history.

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

The AI agent uses the user's saved AI chat history, the current Pointercrate Top
10, the stored daily challenge, recently detected Demonlist update events, and
Mistral web search for recent public information. When public web information is
used, the agent can include source links returned by Mistral. Use `/agent_stop`
to leave chat mode while keeping history, or `/agent_reset` to delete the saved
AI conversation.

## Security Notes

- Store Telegram API credentials and bot tokens in environment variables.
- Store the Mistral AI API key in `MISTRAL_API_KEY`.
- Do not commit real Telegram API credentials, bot tokens, or API keys.
- Rotate a token immediately if it has been shared publicly.
- Treat session and database files as private runtime data.
