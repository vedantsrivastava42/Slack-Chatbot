# Demo Slack Guide — Private Channel Only

Minimal setup so your manager can test the bot in **one private channel** only. No public channels, no DMs.

---

## 1. Create the app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create an App** → **From scratch**.
2. Name it (e.g. "Codebase Query Bot") and pick your workspace → **Create App**.

---

## 2. Enable Socket Mode

1. Left sidebar → **Socket Mode**.
2. Turn **Enable Socket Mode** ON.
3. **Generate Token and Scope** (or Basic Information → App-Level Tokens).
4. Name it (e.g. "socket-mode"), add scope **`connections:write`** → **Generate**.
5. Copy the token (starts with `xapp-`) → this is **`SLACK_APP_TOKEN`**.

---

## 3. Bot scopes (private channel only)

1. Left sidebar → **OAuth & Permissions**.
2. Under **Bot Token Scopes**, add **only** these:
   - **`app_mentions:read`** — See when the bot is @mentioned.
   - **`groups:history`** — Read messages in private channels.
   - **`groups:read`** — Basic info about private channels.
   - **`chat:write`** — Send replies.
   - **`reactions:write`** — Show processing (e.g. eyes reaction).
3. Scroll up → **Install to Workspace** → **Allow**.
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`) → this is **`SLACK_BOT_TOKEN`**.

---

## 4. Events (only what’s needed)

1. Left sidebar → **Event Subscriptions**.
2. Turn **Enable Events** ON.
3. Under **Subscribe to bot events**, add:
   - **`app_mention`**
4. **Save Changes**.

---

## 5. Invite the bot to one private channel

1. Open the **private channel** where the demo will run.
2. Type: `/invite @YourBotName` (use the name you gave the app).
3. Confirm the bot appears in the channel. Use **only this channel** for the demo.

---

## 6. Run the bot

1. In **CHATBOT SERVICE**, create `.env` with at least:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=models/gemini-flash-latest
DEFAULT_REPOSITORY_PATH=/path/to/your/codebase
```

2. Install deps and run:

```bash
pip install -r requirements.txt
python slack_bot.py
```

3. In that **private channel**, mention the bot: `@YourBotName your question`.
4. The bot should reply in the same channel (in thread).

---

## Adding other permissions later

When you want to enable more than the private channel:

1. Go to **OAuth & Permissions** → **Bot Token Scopes** and add the scopes you need.
2. If you add new event types, go to **Event Subscriptions** → **Subscribe to bot events** and add the matching events.
3. Reinstall: **OAuth & Permissions** → **Install to Workspace** → **Allow** (so the new scopes take effect).

| If you want…           | Add these Bot Scopes        | Add these Bot Events  |
|------------------------|-----------------------------|------------------------|
| Public channel mentions| `channels:history`          | (none; `app_mention` already covers it) |
| Direct messages (DMs)  | `im:history`, `im:read`, `im:write` | `message.im`   |
| Group DMs              | `mpim:history`              | `message.mpim`         |

After adding scopes/events, run **Install to Workspace** again, then invite the bot to the new channel or open a DM as needed.
