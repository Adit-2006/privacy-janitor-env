import os
import json
import re
import time
from openai import OpenAI
from server.privacy_janitor_environment import PrivacyJanitorEnvironment
from models import PrivacyJanitorAction

# Official Hackathon Environment Variables for OpenAI-compatible HF API
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME") or "meta-llama/Meta-Llama-3-8B-Instruct"

MAX_STEPS = 25 
TASK_ID = "easy" # Switch to "easy" or "medium" or 'hard' as needed

def extract_json(text_response):
    """Helper to clean up output if the LLM wraps the JSON in markdown blocks."""
    if not text_response:
        return None
    match = re.search(r'\{.*\}', text_response.replace('\n', ''))
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None

def main():
    # Ensure API Key is present
    if not API_KEY:
        print("--- ERROR: API_KEY or HF_TOKEN environment variable is missing ---")
        return

    env = PrivacyJanitorEnvironment()
    obs = env.reset(task_id=TASK_ID)
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # --- EPISODE START (VALIDATOR REQUIRED FORMAT) ---
    print(f"[START] task={TASK_ID}", flush=True)
    print(f"Model: {MODEL_NAME}")
    print(f"Task: Find and redact {env.total_pii_to_find} PII items.")
    print(f"Files in VFS: {obs.files}\n")

    visited_files = []
    total_accumulated_reward = 0.0

    for step in range(1, MAX_STEPS + 1):
        
        prompt = f"""
                You are a strict Data Privacy AI. 
                
                Current Observation:
                Available Files: {obs.files}
                Files Already Checked: {visited_files}
                Content Preview: '{obs.content_preview}'
                Message: {obs.message}
                
                You must respond with ONLY valid JSON.
                Schema: {{"command": "read_file" | "redact", "path": "filename", "pattern": "string_to_redact"}}
                
                CRITICAL RULES:
                1. ANALYZE CONTENT: If the 'Content Preview' contains sensitive data (email, phone, or SSN), redact it.
                2. EXPLORE: If not, "read_file" a file from 'Available Files' NOT in 'Files Already Checked'.
                """
        
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.2
            )
            raw_output = completion.choices[0].message.content or ""
            action_dict = extract_json(raw_output)
            
            if action_dict:
                action = PrivacyJanitorAction(**action_dict)
            else:
                raise ValueError("Could not parse JSON")
                
        except Exception as exc:
            # Fallback exploration logic if the model fails
            unvisited = [f for f in obs.files if f not in visited_files]
            target = unvisited[0] if unvisited else obs.files[0]
            action = PrivacyJanitorAction(command="read_file", path=target, pattern="")
            
        print(f"ACTION: {action.command} on '{action.path}'")
        
        # Update memory
        if action.command == "read_file" and action.path not in visited_files:
            visited_files.append(action.path)
            
        # Environment Step
        obs = env.step(action)
        total_accumulated_reward += obs.reward
        
        # --- STEP LOGGING (VALIDATOR REQUIRED FORMAT) ---
        print(f"[STEP] step={step} reward={obs.reward}", flush=True)
        print(f"OBSERVATION: {obs.message}")
        print(f"PROGRESS: {env.redacted_pii_count}/{env.total_pii_to_find}\n")
        
        if obs.done:
            # --- END EPISODE SUCCESS (VALIDATOR REQUIRED FORMAT) ---
            print(f"[END] task={TASK_ID} score={env.score()} steps={step}", flush=True)
            print(f"Final Redaction Count: {env.redacted_pii_count}")
            print(f"Accumulated Reward: {total_accumulated_reward:.4f}")
            break
            
    else:
        # --- END EPISODE TIMEOUT (VALIDATOR REQUIRED FORMAT) ---
        print(f"[END] task={TASK_ID} score={env.score()} steps={MAX_STEPS}", flush=True)
        print(f"Reached max steps ({MAX_STEPS}).")

if __name__ == "__main__":
    main()
