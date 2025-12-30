"""
Lambda Container Memory Manager
Stores conversation history in-memory for the duration of Lambda execution
Perfect for serverless deployments with thread-aware conversations
"""

import time


class LambdaMemoryManager:
    """
    In-memory conversation storage for Lambda/Serverless deployments.
    Memory persists for the duration of the Lambda execution.
    """
    
    def __init__(self, max_messages=10):
        """
        Initialize the memory manager.
        
        Args:
            max_messages: Maximum number of messages to keep per conversation (default: 10)
        """
        self.conversations = {}  # session_id -> list of messages
        self.max_messages = max_messages
    
    def get_session_id(self, user_id: str, channel_id: str, thread_ts: str = None) -> str:
        """
        Generate a unique session ID for a conversation.
        
        Args:
            user_id: Slack user ID
            channel_id: Slack channel ID
            thread_ts: Thread timestamp (if in a thread) or message timestamp
            
        Returns:
            Session ID string in format: user_id:channel_id:thread_ts
        """
        if not thread_ts:
            # Use channel_id as thread identifier for non-threaded conversations
            thread_ts = channel_id
        return f"{user_id}:{channel_id}:{thread_ts}"
    
    def get_context(self, session_id: str) -> list:
        """
        Retrieve conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of message dictionaries with 'role', 'content', and 'timestamp'
        """
        return self.conversations.get(session_id, [])
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role ('user' or 'assistant')
            content: Message content
        """
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
        """
        Get formatted conversation context as a string for use in queries.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Formatted string with conversation history, or empty string if no history
        """
        messages = self.get_context(session_id)
        if not messages:
            return ""
        
        formatted_lines = []
        for msg in messages:
            role_label = "User" if msg['role'] == 'user' else "Assistant"
            formatted_lines.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(formatted_lines)
    
    def clear_session(self, session_id: str):
        """
        Clear conversation history for a specific session.
        
        Args:
            session_id: Session identifier to clear
        """
        if session_id in self.conversations:
            del self.conversations[session_id]

