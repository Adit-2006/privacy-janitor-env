🧹 Privacy Janitor Environment

A Meta OpenEnv Hackathon Submission

Privacy Janitor is a dynamic, scalable Reinforcement Learning (RL) environment built strictly to the Meta OpenEnv specification.

In this environment, an AI agent acts as an automated data privacy officer. Its mission is to navigate a simulated virtual file system (VFS), locate hidden Personally Identifiable Information (PII) amongst decoy files, and successfully redact the sensitive data using Regular Expressions (Regex) before hitting the step limit.

🚀 Architecture & Compliance Highlights

This submission was explicitly engineered to pass all automated OpenEnv grading requirements:

Dynamic Task Generation: Implements 3 distinct difficulty tiers (easy, medium, hard) using procedural generation to scale the "haystack" (decoy files) and the "needles" (PII) to prevent model memorization.

Strict Grader Compliance: The score() endpoint mathematically tracks PII redaction, returning a strict 0.0 to 1.0 float, with epsilon clamping to allow for partial credit.

Clean State Management: Fully stateless architecture between episodes. State is tracked via a strictly typed Pydantic @property (PrivacyJanitorState), allowing the OpenEnv grader flawless serialization and auditing.

Modern Docker Build: Utilizes a multi-stage BuildKit Dockerfile and the hatchling build backend to safely package flat directories, satisfying strict uv package manager constraints.

🕹️ Action & Observation Space

Sensible Action Space

The agent interacts using a strictly typed Pydantic Action model with two commands:

read_file: Requires a path. Returns the contents of the file into the observation space.

redact: Requires a path and a pattern (regex string). Applies the regex and replaces matches with [REDACTED].

Informative Observation Space

The Observation prevents "cheating" while giving the agent a clear path forward:

files: A list of available files in the current directory.

content_preview: Only populates when the agent explicitly uses the read_file action.

message: Provides instant feedback (e.g., "Redacted 2 instance(s). Progress: 2/5").

🧠 Reward Shaping & Episode Boundaries

This environment is designed for stable RL training with excellent reward shaping:

Incremental Rewards: The agent receives 0.5 * matches for every successful redaction. This creates a breadcrumb trail, teaching the agent it is performing the correct actions before the episode ends.

Completion Bonus: Reaching the required number of redactions yields a max reward of 1.0.

Epsilon Clamping: All rewards are strictly clamped between 0.0001 and 0.9999 to ensure OpenEnv framework compliance and prevent gradient explosions.

Strict Episode Boundaries: Episodes terminate upon absolute success or when a hard step limit (20 steps) is reached.

📁 Repository Structure

privacy-janitor-env/
├── pyproject.toml              # Build backend and dependencies (replaces setuptools)
├── models.py                   # Pydantic schemas (Action, Observation)
├── inference.py                # Baseline agent testing script
├── Dockerfile                  # Official Meta OpenEnv BuildKit instructions
├── README.md                   
└── server/
    ├── app.py                  # OpenEnv FastAPI wrapper
    └── privacy_janitor_environment.py # Core simulation and dynamic generation logic


🚀 How to Run

Via OpenEnv Web Interface

This environment supports the built-in OpenEnv Human-in-the-Loop Web UI for manual testing:

Navigate to the Hugging Face Space endpoint.

Manually trigger read_file and redact commands to test the environment logic.

Via API (RL Agent)

import requests

# 1. Reset the environment (Choose difficulty: easy, medium, hard)
response = requests.post("YOUR_HF_SPACE_URL/reset", json={"task_id": "medium"})
print(response.json())

# 2. Take a step
action = {
    "command": "read_file",
    "path": "logs/app.log"
}
step_response = requests.post("YOUR_HF_SPACE_URL/step", json=action)
print(step_response.json())
