"""Automatically add one random reaction to each eligible group message."""

from __future__ import annotations

import logging
import os
import random
import sqlite3

from telegram import Message, Update
from telegram.constants import ChatType
from telegram.error import TelegramError
from telegram.ext import Application, ContextTypes, MessageHandler, filters

LOGGER = logging.getLogger(__name__)

REACTIONS = ("💋", "💦", "👅", "❤️", "🔥")
GROUP_CHAT_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}

# Telegram service messages are represented as Message objects with one of
# these fields populated. They are not regular user content and cannot
# reliably receive reactions.
SERVICE_MESSAGE_FIELDS = (
    "boost_added",
    "chat_background_set",
    "chat_owner_changed",
    "chat_owner_left",
    "chat_shared",
    "connected_website",
    "delete_chat_photo",
    "direct_message_price_changed",
    "forum_topic_closed",
    "forum_topic_created",
    "forum_topic_edited",
    "forum_topic_reopened",
    "general_forum_topic_hidden",
    "general_forum_topic_unhidden",
    "giveaway",
    "giveaway_completed",
    "giveaway_created",
    "giveaway_winners",
    "group_chat_created",
    "left_chat_member",
    "managed_bot_created",
    "message_auto_delete_timer_changed",
    "migrate_from_chat_id",
    "migrate_to_chat_id",
    "new_chat_members",
    "new_chat_photo",
    "new_chat_title",
    "pinned_message",
    "proximity_alert_triggered",
    "refunded_payment",
    "successful_payment",
    "supergroup_chat_created",
    "users_shared",
    "video_chat_ended",
    "video_chat_participants_invited",
    "video_chat_scheduled",
    "video_chat_started",
    "write_access_allowed",
)

PROCESSED_MESSAGES_DB = "processed_messages.db"
processed_messages_db: sqlite3.Connection | None = None


def _has_value(value: object) -> bool:
    """Return whether a Telegram field contains a meaningful value."""
    if value is None or value is False:
        return False
    if isinstance(value, (list, tuple, set, dict)) and not value:
        return False
    return True


def _is_service_message(message: Message) -> bool:
    """Check whether Telegram marked the message as a service/system event."""
    return any(
        _has_value(getattr(message, field, None))
        for field in SERVICE_MESSAGE_FIELDS
    )


def _open_processed_messages_db() -> sqlite3.Connection:
    """Open the small local ledger used to prevent duplicate reactions."""
    database = sqlite3.connect(PROCESSED_MESSAGES_DB)
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_messages (
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            PRIMARY KEY (chat_id, message_id)
        )
        """
    )
    database.commit()
    return database


def _mark_message_as_processed(message_key: tuple[int, int]) -> bool:
    """Record a message and return False when it was already recorded."""
    if processed_messages_db is None:
        raise RuntimeError("The processed-message database is not initialized.")

    cursor = processed_messages_db.execute(
        """
        INSERT OR IGNORE INTO processed_messages (chat_id, message_id)
        VALUES (?, ?)
        """,
        message_key,
    )
    processed_messages_db.commit()
    return cursor.rowcount == 1


async def react_to_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """React once to each eligible group message without sending a reply."""
    message = update.message
    if message is None or message.chat.type not in GROUP_CHAT_TYPES:
        return

    # The bot's own messages should never trigger another reaction.
    if message.from_user is not None and message.from_user.id == context.bot.id:
        return

    if _is_service_message(message):
        return

    message_key = (message.chat.id, message.message_id)
    try:
        is_new_message = _mark_message_as_processed(message_key)
    except sqlite3.Error:
        LOGGER.exception(
            "Could not record message %s in chat %s; skipping reaction.",
            message.message_id,
            message.chat.id,
        )
        return
    if not is_new_message:
        return

    emoji = random.choice(REACTIONS)
    try:
        await context.bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[emoji],
        )
        LOGGER.info(
            "Added reaction %s to message %s in chat %s.",
            emoji,
            message.message_id,
            message.chat.id,
        )
    except TelegramError as error:
        # A missing permission, unsupported emoji, or message restriction
        # should not stop polling or prevent later messages from processing.
        LOGGER.warning(
            "Could not react to message %s in chat %s: %s",
            message.message_id,
            message.chat.id,
            error,
        )
    except Exception:
        # Keep the bot alive even if an unexpected error occurs.
        LOGGER.exception(
            "Unexpected error while reacting to message %s in chat %s.",
            message.message_id,
            message.chat.id,
        )


async def handle_application_error(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Log unexpected application errors without stopping the bot."""
    LOGGER.error("Unhandled Telegram update error: %s", context.error)


def build_application(bot_token: str) -> Application:
    """Build the long-polling Telegram application."""
    application = Application.builder().token(bot_token).build()
    application.add_handler(
        MessageHandler(filters.ALL, react_to_message)
    )
    application.add_error_handler(handle_application_error)
    return application


def main() -> int:
    """Start the bot using the BOT_TOKEN Replit Secret."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # HTTP request URLs include the bot token in Telegram's API path.
    # Keep request-level logs quiet so secrets never appear in console output.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        LOGGER.error(
            "BOT_TOKEN is not set. Add your BotFather token as a Replit "
            "Secret named BOT_TOKEN, then run the bot again."
        )
        return 1

    global processed_messages_db
    try:
        processed_messages_db = _open_processed_messages_db()
    except sqlite3.Error:
        LOGGER.exception("Could not open the processed-message database.")
        return 1

    LOGGER.info("Starting Telegram auto-reaction bot with long polling.")
    application = build_application(bot_token)
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        processed_messages_db.close()
        processed_messages_db = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())