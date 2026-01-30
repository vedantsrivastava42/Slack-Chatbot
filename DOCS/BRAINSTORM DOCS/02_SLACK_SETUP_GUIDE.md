# Slack Bot Setup Guide

This guide will walk you through setting up the Slack bot for the Codebase Query Service.

## Step-by-Step UI Setup Instructions

### Step 1: Create a Slack App (0:20-0:34)

1. Navigate to [api.slack.com](https://api.slack.com/apps)
2. Click **"Your Apps"** in the top right corner
3. Click **"Create an App"**
4. Select **"From scratch"**
5. Name your app (e.g., "Codebase Query Bot")
6. Select your workspace
7. Click **"Create App"**

### Step 2: Enable Socket Mode and Generate App Token (0:38-1:02)

1. In the left sidebar, click **"Socket Mode"**
2. Toggle **"Enable Socket Mode"** to ON
3. Click **"Generate Token and Scope"** or go to **"Basic Information"** → **"App-Level Tokens"**
4. Click **"Generate Token and Scope"**
5. Name the token (e.g., "socket-mode-token")
6. Add the scope: **`connections:write`**
7. Click **"Generate"**
8. **COPY THIS TOKEN** - You'll need it for `SLACK_APP_TOKEN` in your `.env` file
   - This token starts with `xapp-`

### Step 3: Configure OAuth & Permissions (Bot Token Scopes) (1:08-1:35)

1. In the left sidebar, click **"OAuth & Permissions"**
2. Scroll down to **"Bot Token Scopes"**
3. Click **"Add an OAuth Scope"** and add the following scopes:
   - `app_mentions:read` - Read mentions of your app
   - `channels:history` - View messages in public channels
   - `chat:write` - Send messages as the bot
   - `reactions:write` - Add reactions to messages
   - `im:history` - View messages in DMs
   - `im:read` - View basic information about DMs
   - `im:write` - Send messages in DMs
   - `groups:history` - View messages in private channels
   - `mpim:history` - View messages in group DMs

### Step 4: Install the App to Workspace (1:35-1:43)

1. Scroll up to the top of the **"OAuth & Permissions"** page
2. Click **"Install to Workspace"**
3. Review the permissions and click **"Allow"**
4. **COPY THE BOT USER OAUTH TOKEN** - You'll need it for `SLACK_BOT_TOKEN` in your `.env` file
   - This token starts with `xoxb-`

### Step 5: Setting Up Event Subscriptions (1:45-2:11)

1. In the left sidebar, click **"Event Subscriptions"**
2. Toggle **"Enable Events"** to ON
3. Scroll down to **"Subscribe to bot events"**
4. Click **"Add Bot User Event"** and add the following events:
   - `app_mention` - Subscribe to bot mentions
   - `message.channels` - Messages in public channels
   - `message.groups` - Messages in private channels
   - `message.im` - Direct messages
   - `message.mpim` - Group direct messages
   - `reaction_added` - Reactions added to messages (optional)

5. Click **"Save Changes"** at the bottom

### Step 6: Enable Direct Messages (App Home)

1. In the left sidebar, click **"App Home"**
2. Scroll down to **"Show Tabs"** section
3. Make sure **"Messages Tab"** is enabled (toggle should be ON)
4. Scroll down to **"Home Tab"** section
5. Under **"Allow users to send Slash commands and messages from the messages tab"**, toggle **"Allow users to send messages"** to **ON**
6. Click **"Save Changes"** at the bottom

**Important**: This step is required for users to be able to send direct messages to your bot. Without this, you'll see "Sending messages to this app has been turned off" in DMs.

### Step 7: Personalizing the Bot Icon (2:11-2:18) - Optional

1. In the left sidebar, click **"Basic Information"**
2. Scroll down to **"Display Information"**
3. Upload a custom icon for your bot
4. Add a bot name and description

### Step 8: Invite the Bot to a Slack Channel (2:18-2:26)

1. Go to any Slack channel where you want to use the bot
2. Type: `/invite @YourBotName` (replace with your bot's name)
3. Or click the channel name → **"Integrations"** → **"Add apps"** → Select your bot

## Environment Variables Setup

Create a `.env` file in the `codebase-query-service-python` directory with the following:

```env
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=models/gemini-flash-latest

# Service Configuration
DEFAULT_REPOSITORY_PATH=/path/to/your/repository
ENABLE_READONLY_ENFORCEMENT=true
```

### Where to Find the Tokens:

- **SLACK_BOT_TOKEN**: 
  - Go to **"OAuth & Permissions"** → Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

- **SLACK_APP_TOKEN**: 
  - Go to **"Basic Information"** → **"App-Level Tokens"** → Copy the token you created (starts with `xapp-`)

## Running the Slack Bot

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure your `.env` file is configured with all tokens

3. Run the Slack bot:
   ```bash
   python slack_bot.py
   ```

4. You should see:
   ```
   Starting Slack Bot...
   Repository path: /path/to/repository
   Bot is ready! Mention the bot in a channel or send a DM.
   ```

## Testing the Bot

1. **In a Channel**: Mention your bot with a question:
   ```
   @YourBotName What is the main entry point of this application?
   ```

2. **In a DM**: Send a direct message to your bot:
   ```
   What are the API endpoints in this codebase?
   ```

The bot will:
- Show a reaction (👀 or ⏳) while processing
- Respond with the processed answer in a thread (for mentions) or directly (for DMs)

## Troubleshooting

- **"Sending messages to this app has been turned off"**: 
  - Go to **"App Home"** in your Slack app settings
  - Enable **"Allow users to send messages"** under the Home Tab section
  - Click **"Save Changes"**
  - You may need to close and reopen the DM with the bot

- **Bot not responding**: 
  - Check that Socket Mode is enabled
  - Verify both tokens are correct in `.env`
  - Make sure the bot is invited to the channel

- **Permission errors**: 
  - Verify all required scopes are added in "OAuth & Permissions"
  - Reinstall the app to workspace after adding scopes

- **Connection issues**: 
  - Check your internet connection
  - Verify the app token has `connections:write` scope

