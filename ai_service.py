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
        # Build base prompt
        prompt = f"""You are a helpful code assistant. A user asked: "{user_query}"

The codebase query tool returned the following response:

{raw_response}"""
        
        # Include conversation history if available
        if conversation_context:
            prompt += f"""

Conversation History:
{conversation_context}

Please use the conversation history to understand the context of follow-up questions. If this is a follow-up question, refer back to previous messages to provide a coherent answer."""
        
        prompt += """

Please provide a clear, concise, and helpful answer to the user's question based on the information above.

IMPORTANT FORMATTING RULES:
- Do NOT use markdown formatting like ### (headers) or ** (bold text)
- Do NOT use asterisks, hashes, or other markdown symbols
- Use plain text only - the output will be displayed in Slack
- Keep the font consistent throughout
- Use simple line breaks and spacing for structure
- If the response contains code, format it as plain text code blocks or inline code only

If there are any issues or the response is unclear, please explain that as well."""

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

