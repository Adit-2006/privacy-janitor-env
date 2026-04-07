import os
import json
import re
from openai import OpenAI
from server.privacy_janitor_environment import PrivacyJanitorEnvironment
from models import Action

# 1. Official Hackathon Environment Variables
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME") or "meta-llama/Meta-Llama-3-8B-Instruct"
MAX_STEPS = 10

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
    obs = env.reset(task_id="easy")

    # 2. Explicit Client Initialization as required by the rubric
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"🧹 Privacy Janitor Agent Activated using model: {MODEL_NAME}...\n")
    print(f"Initial State: {obs.message}\n")

    for step in range(1, MAX_STEPS + 1):
        print(f"--- Step {step} ---")
        
        prompt = f"""
                You are a strict Data Privacy AI. 
                
                Current Observation:
                Files: {obs.files}
                Content: {obs.content_preview}
                Message: {obs.message}
                
                You must respond with ONLY valid JSON.
                Schema: {{"command": "read_file" | "redact", "path": "filename", "pattern": "string_to_redact"}}
                
                CRITICAL RULES:
                1. If you haven't read 'logs/app.log' yet, use "read_file".
                2. Look closely at the 'Content' field above. If you see an email address in it, you MUST use the "redact" command immediately. The 'pattern' should be the exact email address.
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
                action = Action(**action_dict)
            else:
                raise ValueError("Could not parse JSON")
                
        except Exception as exc:
            # 3. Fallback Action (Preventing crashes)
            print(f"⚠️ Model request failed or invalid format ({exc}). Using fallback action.")
            # Default to safely reading the root directory if confused
            action = Action(command="read_file", path="logs/app.log")
            
        print(f"🤖 Agent Decided: {action.command} on '{action.path}'")
            
        # Execute the action in the environment
        obs = env.step(action)
        print(f"💰 Reward Earned: {obs.reward_signal}")
        print(f"👀 Result: {obs.message}\n")
        
        if obs.done:
            print("🏁 Task Completed by Agent!")
            break
            
    else:
        print(f"Reached max steps ({MAX_STEPS}).")

# --- DEBUG LAUNCHER ---
if __name__ == "__main__":
    print("🚀 Script is awake! Checking variables...")
    if not API_KEY:
        print("❌ Error: API_KEY or HF_TOKEN environment variable is missing.")
    else:
        print(f"✅ Token found. Attempting to start agent with model: {MODEL_NAME}")
        main()