import asyncio
import logging

asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked

import config
import keyboards
import database

from api import (
    get_top_demons,
    get_all_listed_demons,
    format_demon,
    get_gd_profile,
    format_gd_profile,
    get_random_daily_demon,
    format_daily_challenge
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


bot = Client(
    name="DemonList",
    api_id=config.api_id,
    api_hash=config.api_hash,
    bot_token=config.bot_token
)


waiting_for_profile = set()


def button_filter(button):
    async def func(_, __, message):
        return message.text == button.text

    return filters.create(
        func,
        "ButtonFilter",
        button=button
    )


async def waiting_profile_filter(_, __, message):
    return (
        message.from_user is not None
        and message.from_user.id in waiting_for_profile
        and message.text is not None
    )


waiting_for_profile_input = filters.create(
    waiting_profile_filter,
    "WaitingForProfileInput"
)


async def send_profile(message, nickname: str):
    loading_message = await message.reply(
        f"Searching for `{nickname}`...",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        profile_data = await get_gd_profile(nickname)

        if not profile_data:
            await loading_message.edit_text(
                f"Could not find the profile `{nickname}`.",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await loading_message.edit_text(
            format_gd_profile(profile_data),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

    except Exception as error:
        await loading_message.edit_text(
            f"Could not find the profile `{nickname}`.\n\n"
            "Check the spelling and try again.\n\n"
            f"Error: `{error}`",
            parse_mode=ParseMode.MARKDOWN
        )


async def get_or_create_daily_challenge():
    challenge = database.get_daily_challenge()

    if challenge is not None:
        return challenge

    challenge = await get_random_daily_demon()
    database.save_daily_challenge(challenge)

    return database.get_daily_challenge()

DEMONLIST_CHECK_INTERVAL = 600  # 10 minutes


def get_demon_key(demon: dict):
    """
    Uses Pointercrate ID when available.
    Falls back to the lowercase demon name.
    """
    demon_id = demon.get("id")

    if demon_id is not None:
        return f"id:{demon_id}"

    name = demon.get("name", "Unknown")
    return f"name:{name.lower()}"


def compare_demonlists(old_list: list, new_list: list):
    old_demons = {
        get_demon_key(demon): demon
        for demon in old_list
    }

    new_demons = {
        get_demon_key(demon): demon
        for demon in new_list
    }

    changes = []

    # Newly added demons
    for demon_key, new_demon in new_demons.items():
        if demon_key not in old_demons:
            changes.append(
                {
                    "type": "added",
                    "name": new_demon.get("name", "Unknown"),
                    "new_position": new_demon.get("position")
                }
            )

    # Removed demons
    for demon_key, old_demon in old_demons.items():
        if demon_key not in new_demons:
            changes.append(
                {
                    "type": "removed",
                    "name": old_demon.get("name", "Unknown"),
                    "old_position": old_demon.get("position")
                }
            )

    # Position changes
    for demon_key, new_demon in new_demons.items():
        if demon_key not in old_demons:
            continue

        old_demon = old_demons[demon_key]

        old_position = old_demon.get("position")
        new_position = new_demon.get("position")

        if (
            old_position is not None
            and new_position is not None
            and old_position != new_position
        ):
            changes.append(
                {
                    "type": "moved",
                    "name": new_demon.get("name", "Unknown"),
                    "old_position": old_position,
                    "new_position": new_position
                }
            )

    return changes


def format_demonlist_changes(changes: list):
    lines = ["🚨 **Demonlist Update**", ""]

    added_changes = [
        change for change in changes
        if change["type"] == "added"
    ]

    removed_changes = [
        change for change in changes
        if change["type"] == "removed"
    ]

    moved_changes = [
        change for change in changes
        if change["type"] == "moved"
    ]

    for change in added_changes:
        lines.append(
            f"🆕 **{change['name']}** entered the list "
            f"at **#{change['new_position']}**."
        )

    for change in removed_changes:
        lines.append(
            f"❌ **{change['name']}** left the list. "
            f"It was previously **#{change['old_position']}**."
        )

    for change in moved_changes:
        old_position = change["old_position"]
        new_position = change["new_position"]

        if new_position < old_position:
            direction = "⬆️"
            movement = "moved up"
        else:
            direction = "⬇️"
            movement = "moved down"

        lines.append(
            f"{direction} **{change['name']}** {movement}: "
            f"**#{old_position} → #{new_position}**"
        )

    lines.append("")
    lines.append(
        "Use `/notifications_off` to stop receiving these updates."
    )

    return "\n".join(lines)

async def send_demonlist_notification(text: str):
    subscribers = database.get_notification_subscribers()

    logger.info(
        "Sending Demonlist update to %s subscribers.",
        len(subscribers)
    )

    for telegram_id in subscribers:
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

        except FloodWait as error:
            logger.warning(
                "FloodWait while messaging %s: waiting %s seconds.",
                telegram_id,
                error.value
            )

            await asyncio.sleep(error.value)

            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            except Exception:
                logger.exception(
                    "Could not message subscriber %s after FloodWait.",
                    telegram_id
                )

        except UserIsBlocked:
            logger.info(
                "User %s blocked the bot. Removing subscription.",
                telegram_id
            )

            database.disable_notifications(telegram_id)

        except Exception:
            logger.exception(
                "Could not send notification to user %s.",
                telegram_id
            )

        # Small pause to avoid sending too quickly.
        await asyncio.sleep(0.1)


async def check_demonlist_changes():
    try:
        current_list = await get_all_listed_demons()
    except Exception:
        logger.exception("Initial Demonlist request failed.")
        return

    previous_list = database.get_demonlist_snapshot()

    # The first successful check only saves a baseline.
    # It does not send a huge notification about every demon.
    if previous_list is None:
        database.save_demonlist_snapshot(current_list)
        logger.info("Initial Demonlist snapshot saved.")
        return

    changes = compare_demonlists(
        previous_list,
        current_list
    )

    if not changes:
        logger.info("No Demonlist changes detected.")
        database.save_demonlist_snapshot(current_list)
        return

    notification_text = format_demonlist_changes(changes)

    # Save before sending so the same change is not sent again
    # if Telegram delivery partially fails.
    database.save_demonlist_snapshot(current_list)

    await send_demonlist_notification(notification_text)

    logger.info(
        "Detected and processed %s Demonlist changes.",
        len(changes)
    )


async def demonlist_monitor():
    logger.info("Demonlist monitor started.")

    while True:
        try:
            await check_demonlist_changes()

        except asyncio.CancelledError:
            logger.info("Demonlist monitor stopped.")
            raise

        except Exception:
            logger.exception(
                "Unexpected Demonlist monitoring error."
            )

        await asyncio.sleep(DEMONLIST_CHECK_INTERVAL)

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "Welcome to GD Demon List!\n\n"
        "Use the buttons below to view profiles, challenges, and the live Demonlist.",
        reply_markup=keyboards.panel
    )


@bot.on_message(
    filters.command("top10_levels")
    | button_filter(keyboards.top10_levels)
)
async def top10_levels(client, message):
    loading_message = await message.reply(
        "Loading live Top 10 from Pointercrate..."
    )

    try:
        demons = await get_top_demons(limit=10)

        await loading_message.delete()

        if not demons:
            await message.reply("Pointercrate returned no demons.")
            return

        for demon in demons:
            await message.reply(
                format_demon(demon),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

    except Exception as error:
        await loading_message.edit_text(
            "Could not load the Demonlist right now.\n\n"
            f"Error: `{error}`",
            parse_mode=ParseMode.MARKDOWN
        )


@bot.on_message(filters.command("profile"))
async def profile_command(client, message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.reply(
            "Enter a Geometry Dash nickname after the command.\n\n"
            "Example: `/profile Zoink`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    nickname = parts[1].strip()

    if not nickname:
        await message.reply(
            "Please enter a valid Geometry Dash nickname."
        )
        return

    await send_profile(message, nickname)


@bot.on_message(button_filter(keyboards.player_profile))
async def profile_button(client, message):
    if message.from_user is None:
        return

    waiting_for_profile.add(message.from_user.id)

    await message.reply(
        "Send me the Geometry Dash nickname you want to search for.\n\n"
        "Example: `Zoink`\n\n"
        "Send `/cancel` to cancel.",
        parse_mode=ParseMode.MARKDOWN
    )


@bot.on_message(filters.command("cancel"))
async def cancel_profile_search(client, message):
    if message.from_user is None:
        return

    user_id = message.from_user.id

    if user_id in waiting_for_profile:
        waiting_for_profile.discard(user_id)

        await message.reply(
            "Profile search cancelled.",
            reply_markup=keyboards.panel
        )

    else:
        await message.reply(
            "You do not have an active profile search."
        )


@bot.on_message(
    filters.text
    & waiting_for_profile_input
    & ~filters.command([
        "start",
        "profile",
        "top10_levels",
        "daily",
        "complete",
        "points",
        "cancel"
    ])
)
async def profile_nickname_handler(client, message):
    user_id = message.from_user.id
    nickname = message.text.strip()

    waiting_for_profile.discard(user_id)

    if not nickname:
        await message.reply(
            "Please enter a valid Geometry Dash nickname."
        )
        return

    await send_profile(message, nickname)


@bot.on_message(
    filters.command("daily")
    | button_filter(keyboards.daily_challenge)
)
async def daily_challenge(client, message):
    loading_message = await message.reply(
        "Loading today's challenge..."
    )

    try:
        challenge = await get_or_create_daily_challenge()

        await loading_message.edit_text(
            format_daily_challenge(challenge),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

    except Exception as error:
        await loading_message.edit_text(
            "Could not load today's challenge.\n\n"
            f"Error: `{error}`",
            parse_mode=ParseMode.MARKDOWN
        )


@bot.on_message(
    filters.command("complete")
    | button_filter(keyboards.complete_challenge)
)
async def complete_challenge(client, message):
    if message.from_user is None:
        return

    challenge = database.get_daily_challenge()

    if challenge is None:
        await message.reply(
            "Today's challenge has not been generated yet.\n"
            "Use `/daily` first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    telegram_id = message.from_user.id

    if database.has_completed_today(telegram_id):
        points = database.get_points(telegram_id)

        await message.reply(
            "You already completed today's challenge.\n\n"
            f"Your balance: **{points} points**",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    rewarded = database.complete_daily_challenge(telegram_id)

    if rewarded:
        points = database.get_points(telegram_id)

        await message.reply(
            "✅ **Daily challenge completed!**\n\n"
            "You earned **1 point**.\n"
            f"Your new balance: **{points} points**",
            parse_mode=ParseMode.MARKDOWN
        )

    else:
        await message.reply(
            "You have already received today's point."
        )


@bot.on_message(
    filters.command("points")
    | button_filter(keyboards.points_button)
)
async def points(client, message):
    if message.from_user is None:
        return

    balance = database.get_points(message.from_user.id)

    point_word = "point" if balance == 1 else "points"

    await message.reply(
        "💰 **Your Point Balance**\n\n"
        f"You currently have **{balance} {point_word}**.",
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_message(
    filters.command("notifications_on")
    | button_filter(keyboards.notifications_on)
)
async def notifications_on(client, message):
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    if database.notifications_enabled(telegram_id):
        await message.reply(
            "🔔 Demonlist notifications are already enabled."
        )
        return

    database.enable_notifications(telegram_id)

    await message.reply(
        "🔔 **Demonlist notifications enabled!**\n\n"
        "You will receive a message when a demon enters, "
        "leaves, or changes position.\n\n"
        "Use `/notifications_off` to disable them.",
        parse_mode=ParseMode.MARKDOWN
    )


@bot.on_message(
    filters.command("notifications_off")
    | button_filter(keyboards.notifications_off)
)
async def notifications_off(client, message):
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    if not database.notifications_enabled(telegram_id):
        await message.reply(
            "🔕 Demonlist notifications are already disabled."
        )
        return

    database.disable_notifications(telegram_id)

    await message.reply(
        "🔕 Demonlist notifications disabled."
    )


@bot.on_message(
    filters.command("notifications")
    | button_filter(keyboards.notification_status)
)
async def notification_status(client, message):
    if message.from_user is None:
        return

    enabled = database.notifications_enabled(
        message.from_user.id
    )

    if enabled:
        status = "🔔 **Enabled**"
    else:
        status = "🔕 **Disabled**"

    await message.reply(
        "📢 **Demonlist Notification Status**\n\n"
        f"Current status: {status}\n\n"
        "Enable: `/notifications_on`\n"
        "Disable: `/notifications_off`",
        parse_mode=ParseMode.MARKDOWN
    )

@bot.on_message(filters.regex(r"(?i)^hello$"))
async def hello(client, message):
    await message.reply("Hi")


async def main():
    database.create_tables()

    await bot.start()

    print("GD Demon List bot is running...")

    monitor_task = asyncio.create_task(
        demonlist_monitor()
    )

    try:
        await idle()

    finally:
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        await bot.stop()


if __name__ == "__main__":
    bot.run(main())