"""
AI Service for processing responses using Gemini API
Uses OpenAI SDK format for easy switching between AI providers
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Gemini client using OpenAI SDK
# This allows easy switching to OpenAI by changing the base_url and API key
gemini_client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/"
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")

def process_with_ai(raw_response: str, user_query: str, conversation_context: str = None, mode: str = None) -> str:
    """mode: None = default (product/stakeholder). 'oncall' = fix guide for dev (steps, files/functions, todo)."""
    try:
        if mode == "oncall":
            prompt = f"""
You are formatting a fix guide for a developer handling an oncall or production issue.

Goal:
Turn the codebase query response below into a clear, actionable fix guide. Structure your response as:

1. STEPS TO FIX: What the developer should do, in order (numbered steps).
2. FILES AND FUNCTIONS TO CHECK: List specific file paths and function/class names with a one-line note on what to look for or why it matters.
3. TODO: A short checklist the dev can follow to resolve the issue.

Include actual file paths and function names. If the codebase tool asked a clarifying question, pass that question to the user as your response instead.

A user asked: "{user_query}"

The codebase query tool returned the following response:

{raw_response}"""
        else:
            # Default: product/stakeholder flow
            prompt = f"""
You are a code-aware assistant for non-technical, product-focused stakeholders.

Goal:
Explain the system behavior described below in plain language.
Do NOT show code or implementation details.
If the codebase query tool (cursor) has asked the user a clarifying question back, ask that question to the user again as your response.

Two-tier rule (decide silently before answering):

Use TIER_2 ONLY if the user explicitly asks for detail (e.g. "elaborate", "explain in detail", "step-by-step", "full flow", "conditions").
Otherwise, always use TIER_1.

TIER_1 (default):
- Brief and direct (max ~4-6 sentences)
- Main takeaway only
- No steps, no conditions, no branching logic
- Do NOT mention API / endpoint / service names

TIER_2 (on request):
- Step-by-step flow in correct order
- Conditions and branching allowed
- Explain when and why steps happen
- Mention API / endpoint / service names when relevant; for each, give a one-line explanation of what it does
- Still no code

Always:
- Describe behavior as system actions, not code
- Avoid phrases like “the code does” or “this function”
- Do not mix TIER_1 and TIER_2 styles

A user asked: "{user_query}"

The codebase query tool returned the following response:

{raw_response}"""
        
        # Include conversation history if available
        if conversation_context:
            prompt += f"""

Conversation History:
{conversation_context}

Use the conversation history to handle follow-up questions. If this is a follow-up, refer back to previous messages to give a coherent answer."""
        
        if mode == "oncall":
            prompt += """

Format the fix guide clearly. Use plain text only (no markdown): line breaks and spacing for structure. If the response is unclear or incomplete, say so and give the best guidance you can."""
        else:
            prompt += """

Provide a clear, concise answer to the user's question based on the information above.

FORMATTING (for Slack, plain text only):
- No markdown: no ### headers, ** bold, or asterisks/hashes/backticks for formatting.
- Use line breaks and spacing for structure. For code references: plain text or inline only; do not wrap in backticks.

If the response is unclear or incomplete, say so and explain what you can infer."""

        # Make API call to AI service
        # Note: Works with both Gemini (via base_url) and OpenAI (default base_url)
        response = gemini_client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the response text
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            return raw_response  # Fallback to raw response if AI fails
            
    except Exception as e:
        # If AI API fails, return raw response with a note
        print(f"AI API error: {str(e)}")
        return f"{raw_response}\n\n[Note: AI processing unavailable, showing raw response]"

