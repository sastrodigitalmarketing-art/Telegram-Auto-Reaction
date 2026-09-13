# Telegram Auto Reaction Bot

A simple Telegram bot that automatically adds **one random reaction** to each new group message.

Reactions:
- 💋
- 💦
- 👅
- ❤️
- 🔥

## Configuration

Set the environment variable:

`BOT_TOKEN`

to your Telegram BotFather token.

**Never commit your bot token to GitHub.**

## Run

```bash
pip install -r requirements.txt
python main.py
```

The bot uses long polling and does not send text replies.
