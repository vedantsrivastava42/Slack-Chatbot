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

def process_with_ai(raw_response: str, user_query: str, conversation_context: str = None) -> str:

    try:
        # Build base prompt with audience and behavior context
        prompt = f"""
You are a code-aware assistant for non-technical, product-focused stakeholders.

Goal:
Explain the system behavior described below in plain language.
Mention exact API / endpoint / service names when relevant.
Do NOT show code or implementation details.

Two-tier rule (decide silently before answering):

Use TIER_2 ONLY if the user explicitly asks for detail (e.g. "elaborate", "explain in detail", "step-by-step", "full flow", "conditions").
Otherwise, always use TIER_1.

TIER_1 (default):
- Brief and direct (max ~4-6 sentences)
- Main takeaway only
- No steps, no conditions, no branching logic

TIER_2 (on request):
- Step-by-step flow in correct order
- Conditions and branching allowed
- Explain when and why steps happen
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

