"""
    In-memory conversation storage for Lambda/Serverless deployments.
    Memory persists for the duration of the Lambda execution.
"""

import time

class LambdaMemoryManager:

    def __init__(self, max_messages=10):
        self.conversations = {}  # session_id -> list of messages
        self.max_messages = max_messages

    def get_session_id(self, user_id: str, channel_id: str, thread_ts: str = None) -> str:
        if not thread_ts:
            # Use channel_id as thread identifier for non-threaded conversations
            thread_ts = channel_id
        return f"{user_id}:{channel_id}:{thread_ts}"

    def get_context(self, session_id: str) -> list:
        return self.conversations.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        self.conversations[session_id].append({
            'role': role,
            'content': content,
            'timestamp': time.time()
        })

        # Keep only recent messages (truncate from the beginning)
        if len(self.conversations[session_id]) > self.max_messages:
            self.conversations[session_id] = self.conversations[session_id][-self.max_messages:]

    def get_formatted_context(self, session_id: str) -> str:
        messages = self.get_context(session_id)
        if not messages:
            return ""

        formatted_lines = []
        for msg in messages:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            formatted_lines.append(f"{role_label}: {msg['content']}")

        return "\n".join(formatted_lines)

    def clear_session(self, session_id: str):
        if session_id in self.conversations:
            del self.conversations[session_id]

