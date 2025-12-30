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


def query_codebase(query: str, repository_path: str, timeout: int = 60000) -> dict:
    """Query codebase using cursor-agent with read-only protection"""
    start_time = time.time()
    
    try:
        # Make directory read-only
        if ENABLE_READONLY_ENFORCEMENT:
            subprocess.run(["chmod", "-R", "a-w", repository_path], capture_output=True, timeout=30)
        
        # Execute cursor-agent
        escaped_query = query.replace('"', '\\"').replace('$', '\\$')
        cmd = f'cursor-agent --print --output-format json --workspace "{repository_path}" "{escaped_query}"'
        
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=repository_path)
        
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
            
            # Process the raw response through AI service
            processed_response = process_with_ai(raw_response, query)
            
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

