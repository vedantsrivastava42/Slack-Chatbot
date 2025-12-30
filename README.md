# Codebase Query Service - Slack Bot

A Slack bot that queries codebases using `cursor-agent`. Ask questions about your codebase directly in Slack!

## Features

- Query your codebase via Slack mentions or direct messages
- Uses `cursor-agent` for intelligent code analysis
- Processes responses with AI for clear, concise answers
- Read-only protection for repository safety

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify cursor-agent is installed and authenticated:**
   ```bash
   cursor-agent status
   ```

3. **Configure environment variables:**
   Create a `.env` file:
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

4. **Run the Slack bot:**
   ```bash
   python slack_bot.py
   ```

## Slack Setup

See [SLACK_SETUP_GUIDE.md](SLACK_SETUP_GUIDE.md) for detailed Slack app configuration instructions.

## Usage

### In a Channel
Mention the bot with your question:
```
@YourBotName what is the main entry point of this application?
```

### In a Direct Message
Send a direct message to the bot:
```
What are the API endpoints in this codebase?
```

The bot will:
- Show a reaction (👀 or ⏳) while processing
- Respond with the processed answer in a thread (for mentions) or directly (for DMs)

## Environment Variables

- `SLACK_BOT_TOKEN` - Bot User OAuth Token from Slack (required)
- `SLACK_APP_TOKEN` - App-Level Token for Socket Mode (required)
- `GEMINI_API_KEY` - Gemini API key for response processing (required)
- `GEMINI_MODEL` - Gemini model to use (default: `models/gemini-flash-latest`)
- `DEFAULT_REPOSITORY_PATH` - Path to your codebase repository (required)
- `ENABLE_READONLY_ENFORCEMENT` - Enable read-only protection (default: `true`)

## Architecture

```
Slack → Socket Mode → slack_bot.py → query_codebase() → cursor-agent → AI Processing → Response
```

## Deployment

For serverless deployment options, see deployment documentation.
