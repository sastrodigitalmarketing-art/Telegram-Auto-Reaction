import json
import os
import random
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

REACTIONS = ("💋", "💦", "👅", "❤️", "🔥")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()


def telegram_api(method, payload):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram API connection error: {exc}") from exc

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")

    return result


def process_update(update):
    message = update.get("message")
    if not message:
        return "ignored"

    chat = message.get("chat", {})
    if chat.get("type") not in ("group", "supergroup"):
        return "ignored"

    # Don't react to messages sent by bots.
    sender = message.get("from") or {}
    if sender.get("is_bot"):
        return "ignored"

    # Skip Telegram service messages.
    service_fields = (
        "new_chat_members",
        "left_chat_member",
        "new_chat_title",
        "new_chat_photo",
        "delete_chat_photo",
        "group_chat_created",
        "supergroup_chat_created",
        "channel_chat_created",
        "migrate_to_chat_id",
        "migrate_from_chat_id",
        "pinned_message",
        "message_auto_delete_timer_changed",
        "video_chat_started",
        "video_chat_ended",
        "video_chat_participants_invited",
        "forum_topic_created",
        "forum_topic_closed",
        "forum_topic_reopened",
        "general_forum_topic_hidden",
        "general_forum_topic_unhidden",
    )
    if any(field in message for field in service_fields):
        return "ignored"

    emoji = random.choice(REACTIONS)

    telegram_api(
        "setMessageReaction",
        {
            "chat_id": chat["id"],
            "message_id": message["message_id"],
            "reaction": [{"type": "emoji", "emoji": emoji}],
            "is_big": False,
        },
    )

    return emoji


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        # Simple health check.
        self._send_json(200, {"ok": True, "service": "telegram-auto-reaction"})
        return

    def do_POST(self):
        if WEBHOOK_SECRET:
            supplied_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if supplied_secret != WEBHOOK_SECRET:
                self._send_json(401, {"ok": False, "error": "unauthorized"})
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                self._send_json(400, {"ok": False, "error": "empty body"})
                return

            raw = self.rfile.read(length)
            update = json.loads(raw.decode("utf-8"))
            result = process_update(update)

            self._send_json(200, {"ok": True, "result": result})
        except Exception as exc:
            # A non-2xx response tells Telegram to retry delivery.
            print(f"Webhook error: {exc}")
            self._send_json(500, {"ok": False, "error": "processing failed"})
        return
