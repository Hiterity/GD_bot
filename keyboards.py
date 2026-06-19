from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton


top10_levels = KeyboardButton("🏆 Top 10 Demons")
player_profile = KeyboardButton("👤 Player Profile")
daily_challenge = KeyboardButton("🔥 Daily Challenge")
complete_challenge = KeyboardButton("✅ Complete Challenge")
points_button = KeyboardButton("💰 My Points")

notifications_on = KeyboardButton("🔔 Enable Notifications")
notifications_off = KeyboardButton("🔕 Disable Notifications")
notification_status = KeyboardButton("📢 Notification Status")


panel = ReplyKeyboardMarkup(
    [
        [top10_levels, player_profile],
        [daily_challenge, complete_challenge],
        [points_button],
        [notifications_on, notifications_off],
        [notification_status]
    ],
    resize_keyboard=True
)