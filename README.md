# Telegram Auto-Reaction Bot — Vercel

A simple Telegram bot that reacts to new messages in groups/supergroups with exactly **one random emoji** from:

- 💋
- 💦
- 👅
- ❤️
- 🔥

It uses a **Telegram webhook** instead of long polling, so it fits Vercel's serverless model.

## Important

- Keep your Telegram bot token secret.
- Do not put the token in this repository.
- Add the token in Vercel as an Environment Variable named `BOT_TOKEN`.
- The bot should be an administrator in the Telegram group so it can receive group messages reliably.
- Stop any other copy of the same bot that is using long polling before switching to this webhook version.

## Deploy on Vercel

1. Push this project to a GitHub repository.
2. In Vercel, import that GitHub repository.
3. Keep the project on the **Hobby/free** plan for a personal/non-commercial bot.
4. Add this Environment Variable:
   - Name: `BOT_TOKEN`
   - Value: your BotFather token
   - Environment: Production
5. Recommended security variable:
   - Name: `WEBHOOK_SECRET`
   - Value: choose a long random string using letters, numbers, `_` or `-`
   - Environment: Production
6. Deploy.

After deployment, Vercel will give you a URL such as:

`https://your-project.vercel.app`

Your webhook endpoint is:

`https://your-project.vercel.app/api/webhook`

## Connect Telegram to the Vercel webhook

Open this in your browser, replacing the placeholders:

`https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook?url=https%3A%2F%2FYOUR_PROJECT.vercel.app%2Fapi%2Fwebhook&secret_token=YOUR_WEBHOOK_SECRET`

If you did not create `WEBHOOK_SECRET`, leave off `&secret_token=YOUR_WEBHOOK_SECRET`.

A successful response should contain:

`"ok":true`

## Test

Send a normal message in your Telegram group.

The bot should add exactly one randomly selected reaction:

💋 / 💦 / 👅 / ❤️ / 🔥

The function also supports a simple health check. Opening:

`https://your-project.vercel.app/api/webhook`

should return JSON showing `"ok": true`.

## If it doesn't react

Check these in order:

1. Confirm `BOT_TOKEN` is correct in Vercel.
2. Confirm the Vercel deployment succeeded.
3. Confirm the webhook was set successfully.
4. Confirm the bot is in the group.
5. Make the bot an administrator in the group.
6. Check Vercel Runtime Logs for errors.
7. Check Telegram webhook status with:

`https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo`

## Free-plan note

Vercel's Hobby plan is free for personal/non-commercial use. This bot is event-driven: Telegram calls the Vercel function only when an update arrives, instead of keeping a server process running continuously.

For current Vercel limits and plan rules, see Vercel's official documentation.
