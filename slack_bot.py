"""
Slack Bot for Codebase Query Service
Integrates with Slack to answer codebase queries
"""

import os
import ssl
import certifi
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web import WebClient
from dotenv import load_dotenv
from query_service import query_codebase, DEFAULT_REPOSITORY_PATH, DEFAULT_TIMEOUT

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in environment variables")

ssl_context = ssl.create_default_context(cafile=certifi.where())
web_client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)
app = App(client=web_client)

def extract_query_from_mention(text: str, bot_user_id: str) -> str:
    """Extract the actual query from a Slack mention message"""
    query = text.replace(f"<@{bot_user_id}>", "").strip()
    query = query.replace("@AI Agent", "").strip()
    return query

# Handle when the bot is mentioned in a channel
@app.event("app_mention")
def handle_app_mention(event, say):
    """Handle when the bot is mentioned in a channel"""
    try:
        auth_response = app.client.auth_test()
        bot_user_id = auth_response["user_id"]
        query = extract_query_from_mention(event["text"], bot_user_id)
        
        if not query:
            say("Hi! I'm ready to help you query the codebase. Just mention me with your question!")
            return

        try:
            app.client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="eyes")
        except Exception:
            pass
        
        result = query_codebase(query, DEFAULT_REPOSITORY_PATH, DEFAULT_TIMEOUT)

        try:
            app.client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="eyes")
        except Exception:
            pass
        
        if result["success"]:
            say(text=result["response"], thread_ts=event["ts"])
        else:
            say(text=f"Sorry, I encountered an error: {result.get('error', 'Unknown error')}", thread_ts=event["ts"])
    except Exception as e:
        say(text=f"Sorry, I encountered an error processing your request: {str(e)}", thread_ts=event.get("ts"))


# Handle direct messages to the bot (DMs)
@app.event("message")
def handle_message(event, say):
    """Handle direct messages to the bot"""
    if event.get("bot_id") or (event.get("subtype") and event.get("subtype") != "message_changed"):
        return
    
    channel_type = event.get("channel_type")
    channel = event.get("channel", "")
    is_dm = channel_type == "im" or (channel and channel.startswith("D"))
    
    if not is_dm:
        return
    
    try:
        query = event.get("text", "").strip()
        
        if not query:
            say("Hi! I'm ready to help you query the codebase. Just send me your question!")
            return
        
        try:
            app.client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="hourglass_flowing_sand")
        except Exception:
            pass
        
        result = query_codebase(query, DEFAULT_REPOSITORY_PATH, DEFAULT_TIMEOUT)
        
        try:
            app.client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="hourglass_flowing_sand")
        except Exception:
            pass
        
        if result["success"]:
            say(text=result["response"])
        else:
            say(text=f"Sorry, I encountered an error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        say(text=f"Sorry, I encountered an error processing your request: {str(e)}")


def start_slack_bot():
    """Start the Slack bot using Socket Mode"""
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    start_slack_bot()