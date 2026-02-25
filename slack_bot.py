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
from memory_manager import MemoryManager

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in environment variables")

ssl_context = ssl.create_default_context(cafile=certifi.where())
web_client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)
app = App(client=web_client)

# Initialize memory manager with configurable message limit
MAX_CONVERSATION_MESSAGES = int(os.getenv("MAX_CONVERSATION_MESSAGES", "10"))
memory_manager = MemoryManager(max_messages=MAX_CONVERSATION_MESSAGES)

def extract_query_from_mention(text: str, bot_user_id: str) -> str:
    """Extract the actual query from a Slack mention message"""
    query = text.replace(f"<@{bot_user_id}>", "").strip()
    query = query.replace("@AI Agent", "").strip()
    return query


def process_query(event, say, query: str, empty_query_message: str, reaction_emoji: str, use_thread: bool = False):
    """Shared query processing logic for both mentions and direct messages"""
    if not query:
        say(empty_query_message)
        return

    # Generate session ID from thread only (everyone in same thread shares context)
    thread_ts = event.get("thread_ts") or event.get("ts")
    session_id = memory_manager.get_session_id(thread_ts)
    
    # Store user message in memory
    memory_manager.add_message(session_id, "user", query)
    
    # Retrieve conversation context
    conversation_context = memory_manager.get_formatted_context(session_id)

    # Show processing indicator
    try:
        app.client.reactions_add(channel=event["channel"], timestamp=event["ts"], name=reaction_emoji)
    except Exception:
        pass
    
    # Execute query
    result = query_codebase(query, DEFAULT_REPOSITORY_PATH, DEFAULT_TIMEOUT, conversation_context)

    # Remove processing indicator
    try:
        app.client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name=reaction_emoji)
    except Exception:
        pass
    
    # Handle response
    if result["success"]:
        # Store bot response in memory
        memory_manager.add_message(session_id, "assistant", result["response"])
        if use_thread:
            say(text=result["response"], thread_ts=event["ts"])
        else:
            say(text=result["response"])
    else:
        error_message = f"Sorry, I encountered an error: {result.get('error', 'Unknown error')}"
        if use_thread:
            say(text=error_message, thread_ts=event["ts"])
        else:
            say(text=error_message)


# Handle when the bot is mentioned in a channel
@app.event("app_mention")
def handle_app_mention(event, say):
    """Handle when the bot is mentioned in a channel"""
    try:
        auth_response = app.client.auth_test()
        bot_user_id = auth_response["user_id"]
        query = extract_query_from_mention(event["text"], bot_user_id)
        
        process_query(
            event=event,
            say=say,
            query=query,
            empty_query_message="Hi! I'm ready to help you query the codebase. Just mention me with your question!",
            reaction_emoji="eyes",
            use_thread=True
        )
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
        
        process_query(
            event=event,
            say=say,
            query=query,
            empty_query_message="Hi! I'm ready to help you query the codebase. Just send me your question!",
            reaction_emoji="hourglass_flowing_sand",
            use_thread=False
        )
    except Exception as e:
        say(text=f"Sorry, I encountered an error processing your request: {str(e)}")


def start_slack_bot():
    """Start the Slack bot using Socket Mode"""
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    start_slack_bot()