import os
import json
import re
from openai import OpenAI
from server.privacy_janitor_environment import PrivacyJanitorEnvironment
from models import PrivacyJanitorAction

# 1. Official Hackathon Environment Variables
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME") or "meta-llama/Meta-Llama-3-8B-Instruct"
MAX_STEPS = 25

def extract_json(text_response):
    """Helper to clean up output if the LLM wraps the JSON in markdown blocks."""
    match = re.search(r'\{.*\}', text_response.replace('\n', ''))
    if match:
        return json.loads(match.group(0))
    try:
        return json.loads(text_response)
    except json.JSONDecodeError:
        return None

def main():
    env = PrivacyJanitorEnvironment()
    obs = env.reset(task_id="easy")  # You can choose "easy", "medium", or "hard"

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"🧹 Privacy Janitor Agent Activated using model: {MODEL_NAME}...\n")
    print(f"Initial State: {obs.message}\n")

    # NEW: We give the agent memory to track what it has already checked
    visited_files = []
    current_target = None

    for step in range(1, MAX_STEPS + 1):
        print(f"--- Step {step} ---")
        
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
                1. ANALYZE CONTENT: If the 'Content Preview' contains sensitive data (like an email, phone number, or SSN), immediately output a JSON with the "redact" command. The 'path' must be the file you just read, and the 'pattern' must be the exact sensitive string.
                2. EXPLORE: If the 'Content Preview' does NOT contain sensitive data, or is empty, pick a new file from 'Available Files' that is NOT in 'Files Already Checked' and output a JSON with the "read_file" command to inspect it.
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
            print(f"⚠️ Model request failed or invalid format ({exc}). Using fallback.")
            # Fallback to reading a random unvisited file
            unvisited = [f for f in obs.files if f not in visited_files]
            fallback_target = unvisited[0] if unvisited else obs.files[0]
            action = PrivacyJanitorAction(command="read_file", path=fallback_target, pattern="")
            
        print(f"🤖 Agent Decided: {action.command} on '{action.path}'")
        
        # NEW: Update the agent's memory
        if action.command == "read_file" and action.path not in visited_files:
            visited_files.append(action.path)
            current_target = action.path
            
        # Execute the action in the environment
        obs = env.step(action)
        print(f"💰 Reward Earned: {obs.reward}")
        print(f"👀 Result: {obs.message}\n")
        
        if obs.done:
            print("🏁 Task Completed by Agent!")
            break
            
    else:
        print(f"Reached max steps ({MAX_STEPS}).")

if __name__ == "__main__":
    if not API_KEY:
        print("❌ Error: API_KEY or HF_TOKEN environment variable is missing.")
    else:
        main()
