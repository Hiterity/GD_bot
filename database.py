import sqlite3
from datetime import date

DATABASE_NAME = "gd_bot.db"


def connect():
    return sqlite3.connect(DATABASE_NAME)


def create_tables():
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                points INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_challenges (
                challenge_date TEXT PRIMARY KEY,
                demon_name TEXT NOT NULL,
                position INTEGER,
                verifier TEXT,
                publisher TEXT,
                video TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS completions (
                telegram_id INTEGER NOT NULL,
                challenge_date TEXT NOT NULL,
                PRIMARY KEY (telegram_id, challenge_date)
            )
            """
        )

        connection.commit()

    create_notification_tables()


def get_today_string():
    return date.today().isoformat()


def save_daily_challenge(challenge: dict):
    challenge_date = get_today_string()

    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO daily_challenges (
                challenge_date,
                demon_name,
                position,
                verifier,
                publisher,
                video
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                challenge_date,
                challenge.get("name", "Unknown"),
                challenge.get("position"),
                challenge.get("verifier", "Unknown"),
                challenge.get("publisher", "Unknown"),
                challenge.get("video", "")
            )
        )

        connection.commit()


def get_daily_challenge():
    challenge_date = get_today_string()

    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT demon_name, position, verifier, publisher, video
            FROM daily_challenges
            WHERE challenge_date = ?
            """,
            (challenge_date,)
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "name": row[0],
        "position": row[1],
        "verifier": row[2],
        "publisher": row[3],
        "video": row[4]
    }


def has_completed_today(telegram_id: int):
    challenge_date = get_today_string()

    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM completions
            WHERE telegram_id = ?
              AND challenge_date = ?
            """,
            (telegram_id, challenge_date)
        )

        return cursor.fetchone() is not None


def complete_daily_challenge(telegram_id: int):
    challenge_date = get_today_string()

    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO users (telegram_id, points)
            VALUES (?, 0)
            """,
            (telegram_id,)
        )

        cursor.execute(
            """
            SELECT 1
            FROM completions
            WHERE telegram_id = ?
              AND challenge_date = ?
            """,
            (telegram_id, challenge_date)
        )

        if cursor.fetchone() is not None:
            return False

        cursor.execute(
            """
            INSERT INTO completions (telegram_id, challenge_date)
            VALUES (?, ?)
            """,
            (telegram_id, challenge_date)
        )

        cursor.execute(
            """
            UPDATE users
            SET points = points + 1
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        connection.commit()
        return True


def get_points(telegram_id: int):
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO users (telegram_id, points)
            VALUES (?, 0)
            """,
            (telegram_id,)
        )

        cursor.execute(
            """
            SELECT points
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        row = cursor.fetchone()
        connection.commit()

    return row[0] if row else 0

import json


def create_notification_tables():
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_subscribers (
                telegram_id INTEGER PRIMARY KEY
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
            """
        )

        connection.commit()


def enable_notifications(telegram_id: int):
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO notification_subscribers (telegram_id)
            VALUES (?)
            """,
            (telegram_id,)
        )

        connection.commit()


def disable_notifications(telegram_id: int):
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM notification_subscribers
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        connection.commit()


def notifications_enabled(telegram_id: int) -> bool:
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM notification_subscribers
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        return cursor.fetchone() is not None


def get_notification_subscribers():
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT telegram_id
            FROM notification_subscribers
            """
        )

        rows = cursor.fetchall()

    return [row[0] for row in rows]


def save_demonlist_snapshot(demons: list):
    snapshot = []

    for demon in demons:
        snapshot.append(
            {
                "id": demon.get("id"),
                "name": demon.get("name", "Unknown"),
                "position": demon.get("position")
            }
        )

    snapshot_json = json.dumps(snapshot)

    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO bot_settings (setting_key, setting_value)
            VALUES ('demonlist_snapshot', ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
            """,
            (snapshot_json,)
        )

        connection.commit()


def get_demonlist_snapshot():
    with connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT setting_value
            FROM bot_settings
            WHERE setting_key = 'demonlist_snapshot'
            """
        )

        row = cursor.fetchone()

    if row is None:
        return None

    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return None