"""
Codebase Query Service
Uses cursor-agent with --print flag to query codebases
"""

import subprocess
import os
import time
import json
from pathlib import Path
from ai_service import process_with_ai

# Default repository path
DEFAULT_REPOSITORY_PATH = os.getenv(
    "DEFAULT_REPOSITORY_PATH",
    str(Path(__file__).parent.parent / "NinjasTool")
)

# Default timeout (5 minutes)
DEFAULT_TIMEOUT = 600000  # milliseconds

# Enable read-only enforcement via file system permissions
ENABLE_READONLY_ENFORCEMENT = os.getenv("ENABLE_READONLY_ENFORCEMENT", "true").lower() == "true"

# Context sent to cursor-agent so its response aligns with our audience (non-technical, no codebase access)
CURSOR_AUDIENCE_PROMPT = """
You are a code-aware assistant for non-technical, product-focused stakeholders.

Crux: Plain language only, no code. Default = brief (8-10 sentences, main takeaway). 
If they ask for detail, give step-by-step. Describe system behavior; explain any api/function name you mention in short keeping in mind the user does not have codebase access.

Goal:
Explain the system behavior described below in plain language. If you find question ambiguous, ask back questions (only if needed).

User question:
"""

# Prompt for oncall/issue flow: concise dev fix guide (steps, files/functions, todo)
CURSOR_ONCALL_PROMPT = """
The user is asking about an oncall or production issue and needs a short, scannable fix guide for a developer.

Goal: Search the codebase and return a concise fix guide. Keep it brief so a dev can act quickly.

Structure your answer as:
1. STEPS TO FIX: Max 5 steps, one line each. Put the most likely fix first; "if that fails" checks after.
2. FILES AND FUNCTIONS TO CHECK: Max 4–5 entries (path + function/method + one-line why).
3. TODO: Max 4 actionable items (e.g. confirm X, run Y). Put tech-debt (e.g. add Sentry) in a short FOLLOW-UP at the end.

Use actual file paths and function/class names. Be specific but concise.

User question:
"""


def _is_oncall_or_issue(query: str) -> bool:
    """Return True if the query is about oncall or an issue (fix/debug flow)."""
    if not query or not query.strip():
        return False
    q = query.lower().strip()
    triggers = ("oncall", "on-call", "on call", "issue", "fix", "error", "incident", "bug", "broken")
    return any(t in q for t in triggers)


def query_codebase(query: str, repository_path: str, timeout: int = 60000, conversation_context: str = None) -> dict:
    """Query codebase using cursor-agent with read-only protection"""
    start_time = time.time()
    
    try:
        # Make directory read-only
        if ENABLE_READONLY_ENFORCEMENT:
            subprocess.run(["chmod", "-R", "a-w", repository_path], capture_output=True, timeout=30)
        
        # Decision: oncall/issue flow vs default (product/stakeholder) flow
        is_oncall_flow = _is_oncall_or_issue(query)
        cursor_prompt = CURSOR_ONCALL_PROMPT if is_oncall_flow else CURSOR_AUDIENCE_PROMPT

        # Build enhanced query: chosen prompt + user query + optional conversation history
        enhanced_query = cursor_prompt + query
        if conversation_context:
            enhanced_query += "\n\nPrevious conversation:\n" + conversation_context
        
        # Execute cursor-agent using list arguments (prevents command injection)
        # Note: No shell=True, no string escaping needed - subprocess handles arguments safely
        # Use 'auto' model to avoid Opus usage limits
        cursor_model = os.getenv("CURSOR_AGENT_MODEL", "auto")
        process = subprocess.Popen(
            [
                'cursor-agent',
                '--print',
                '--output-format',
                'json',
                '--model',
                cursor_model,
                '--workspace',
                repository_path,
                enhanced_query  # Query passed as single argument, safe from injection
            ],
            shell=False,  # Critical: Prevents command injection
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=repository_path
        )
        
        try:
            stdout_data, stderr_data = process.communicate(timeout=timeout / 1000)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise TimeoutError(f"Query timeout after {timeout}ms")
        
        execution_time = int((time.time() - start_time) * 1000)
        
        if process.returncode == 0:
            try:
                parsed = json.loads(stdout_data.strip())
                raw_response = parsed.get('result') if parsed.get('type') == 'result' else parsed.get('response') or parsed.get('content') or parsed.get('text') or json.dumps(parsed, indent=2)
                raw_response = raw_response or "No response"
            except json.JSONDecodeError:
                raw_response = stdout_data.strip() or stderr_data.strip() or "Empty response"
            
            # Process the raw response through AI service (oncall mode gets fix-guide formatting)
            processed_response = process_with_ai(
                raw_response, query, conversation_context, mode="oncall" if is_oncall_flow else None
            )
            
            return {"success": True, "response": processed_response, "executionTime": execution_time}
        else:
            return {"success": False, "error": stderr_data or f"Process exited with code {process.returncode}", "executionTime": execution_time}
            
    except TimeoutError as e:
        return {"success": False, "error": str(e), "executionTime": int((time.time() - start_time) * 1000)}
    except Exception as e:
        return {"success": False, "error": f"Failed to execute cursor-agent: {str(e)}", "executionTime": int((time.time() - start_time) * 1000)}
    finally:
        if ENABLE_READONLY_ENFORCEMENT:
            subprocess.run(["chmod", "-R", "u+w", repository_path], capture_output=True, timeout=30)

