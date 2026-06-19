import aiohttp
import random

POINTERCRATE_BASE_URL = "https://pointercrate.com/api/v2"


async def get_top_demons(limit=10):
    url = f"{POINTERCRATE_BASE_URL}/demons/listed/"

    headers = {
        "Accept": "application/json",
        "User-Agent": "TelegramGDbot/1.0"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, params={"limit": limit}) as response:
            response.raise_for_status()
            return await response.json()

async def get_all_listed_demons():
    first_page = await fetch_json(
        f"{POINTERCRATE_BASE_URL}/demons/listed/",
        params={
            "limit": 100
        }
    )

    if not first_page:
        return []

    last_position = first_page[-1].get("position")

    second_page = await fetch_json(
        f"{POINTERCRATE_BASE_URL}/demons/listed/",
        params={
            "limit": 100,
            "after": last_position
        }
    )

    demons = first_page + second_page

    return sorted(
        demons,
        key=lambda demon: demon.get("position", 999999)
    )

def format_demon(demon):
    position = demon.get("position", "?")
    name = demon.get("name", "Unknown")

    verifier = demon.get("verifier")
    verifier_name = verifier.get("name", "Unknown") if isinstance(verifier, dict) else "Unknown"

    publisher = demon.get("publisher")
    publisher_name = publisher.get("name", "Unknown") if isinstance(publisher, dict) else "Unknown"

    video = demon.get("video", "No video")

    return (
        f"**#{position} — {name}**\n"
        f"Verified by: `{verifier_name}`\n"
        f"Published by: `{publisher_name}`\n"
        f"Video: {video}"
    )

import aiohttp

POINTERCRATE_BASE_URL = "https://pointercrate.com/api/v2"
GDBROWSER_BASE_URL = "https://gdbrowser.com/api"


async def fetch_json(url: str, params: dict | None = None):
    headers = {
        "Accept": "application/json",
        "User-Agent": "TelegramGDbot/1.0"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, params=params, timeout=20) as response:
            response.raise_for_status()
            return await response.json()


async def get_top_demons(limit=10):
    url = f"{POINTERCRATE_BASE_URL}/demons/listed/"
    return await fetch_json(url, params={"limit": limit})


def get_player_name(value):
    if isinstance(value, dict):
        return value.get("name", "Unknown")
    return value or "Unknown"


def format_demon(demon):
    position = demon.get("position", "?")
    name = demon.get("name", "Unknown")
    requirement = demon.get("requirement", "?")

    verifier_name = get_player_name(demon.get("verifier"))
    publisher_name = get_player_name(demon.get("publisher"))
    video = demon.get("video") or "No video"

    return (
        f"**#{position} — {name}**\n"
        f"Verified by: `{verifier_name}`\n"
        f"Published by: `{publisher_name}`\n"
        f"Record requirement: `{requirement}%`\n"
        f"Video: {video}"
    )


async def get_gd_profile(nickname: str):
    # GDBrowser profile endpoint uses username here.
    url = f"{GDBROWSER_BASE_URL}/profile/{nickname}"
    return await fetch_json(url)


def format_gd_profile(profile: dict):
    username = profile.get("username", "Unknown")
    player_id = profile.get("playerID", "Unknown")
    account_id = profile.get("accountID", "Unknown")

    stars = profile.get("stars", 0)
    demons = profile.get("demons", 0)
    diamonds = profile.get("diamonds", 0)
    coins = profile.get("coins", 0)
    user_coins = profile.get("userCoins", 0)
    secret_coins = profile.get("secretCoins", 0)

    creator_points = profile.get("cp", 0)
    rank = profile.get("rank", "Unknown")

    youtube = profile.get("youtube")
    twitter = profile.get("twitter")
    twitch = profile.get("twitch")

    socials = []
    if youtube:
        socials.append(f"YouTube: {youtube}")
    if twitter:
        socials.append(f"Twitter: {twitter}")
    if twitch:
        socials.append(f"Twitch: {twitch}")

    socials_text = "\n".join(socials) if socials else "No socials found"

    return (
        f"**{username}'s Geometry Dash Profile**\n\n"
        f"Player ID: `{player_id}`\n"
        f"Account ID: `{account_id}`\n"
        f"Rank: `{rank}`\n\n"
        f"⭐ Stars: `{stars}`\n"
        f"😈 Demons: `{demons}`\n"
        f"💎 Diamonds: `{diamonds}`\n"
        f"🪙 Coins: `{coins}`\n"
        f"🔵 User Coins: `{user_coins}`\n"
        f"🟡 Secret Coins: `{secret_coins}`\n"
        f"🛠 Creator Points: `{creator_points}`\n\n"
        f"**Socials**\n"
        f"{socials_text}"
    )

async def get_random_daily_demon():
    demons = await get_top_demons(limit=100)

    if not demons:
        raise ValueError("Pointercrate returned no demons.")

    demon = random.choice(demons)

    verifier = get_player_name(demon.get("verifier"))
    publisher = get_player_name(demon.get("publisher"))

    return {
        "name": demon.get("name", "Unknown"),
        "position": demon.get("position"),
        "verifier": verifier,
        "publisher": publisher,
        "video": demon.get("video") or ""
    }


def format_daily_challenge(challenge: dict):
    name = challenge.get("name", "Unknown")
    position = challenge.get("position", "?")
    verifier = challenge.get("verifier", "Unknown")
    publisher = challenge.get("publisher", "Unknown")
    video = challenge.get("video") or "No video available"

    return (
        "🔥 **Daily Challenge**\n\n"
        f"**#{position} — {name}**\n"
        f"Verified by: `{verifier}`\n"
        f"Published by: `{publisher}`\n"
        f"Verification video: {video}\n\n"
        "Complete the challenge and use `/complete` to earn **1 point**.\n"
        "You can only earn one point from each daily challenge."
    )