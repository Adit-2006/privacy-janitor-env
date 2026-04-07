---
title: Privacy Janitor Environment
emoji: 🧹
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Privacy Janitor Environment

🧹 **Privacy Janitor Environment**

A Meta OpenEnv Hackathon submission.

Privacy Janitor is a dynamic, scalable Reinforcement Learning (RL) environment built to the Meta OpenEnv specification. In this environment, an AI agent acts as an automated data privacy officer. Its mission is to navigate a simulated virtual file system (VFS), locate hidden Personally Identifiable Information (PII) among decoy files, and redact the sensitive data using regular expressions (regex) before hitting the step limit.

## 🚀 Architecture & Compliance Highlights

This submission was explicitly engineered to pass automated OpenEnv grading requirements.

- **Dynamic Task Generation**: Implements three difficulty tiers (`easy`, `medium`, `hard`) using procedural generation to scale the "haystack" (decoy files) and the "needles" (PII), preventing model memorization.
- **Strict Grader Compliance**: The `score()` endpoint tracks PII redaction and returns a strict `0.0` to `1.0` float, with epsilon clamping to allow for partial credit.
- **Clean State Management**: Fully stateless between episodes. State is tracked via a Pydantic `@property` (`PrivacyJanitorState`), enabling reliable grader serialization and auditing.
- **Modern Docker Build**: Uses a multi-stage BuildKit `Dockerfile` and the Hatchling build backend to package flat directories safely and satisfy strict package constraints.

## 🕹️ Action & Observation Space

### Sensible Action Space

The agent interacts with a strongly typed Pydantic `Action` model using two commands:

- `read_file`
  - Requires a `path`
  - Returns file contents into the observation space
- `redact`
  - Requires a `path` and a `pattern` (regex string)
  - Applies the regex and replaces matches with `[REDACTED]`

### Informative Observation Space

The observation is designed to prevent cheating while giving the agent a clear path forward.

- `files`: list of available files in the current directory
- `content_preview`: only populated when the agent explicitly uses `read_file`
- `message`: instant feedback such as `Redacted 2 instance(s). Progress: 2/5`

## 🧠 Reward Shaping & Episode Boundaries

This environment is optimized for stable RL training.

- **Incremental Rewards**: The agent receives `0.5 * matches` for every successful redaction, creating a reward trail that teaches correct behavior before episodes end.
- **Completion Bonus**: Successfully hitting the required redactions yields a maximum reward of `1.0`.
- **Epsilon Clamping**: All rewards are clamped between `0.0001` and `0.9999` to satisfy OpenEnv compliance and prevent gradient instability.
- **Strict Episode Boundaries**: Episodes terminate on success or when the hard step limit of `20` steps is reached.

## 📁 Repository Structure

```text
privacy-janitor-env/
├── pyproject.toml                      # Build backend and dependencies
├── models.py                           # Pydantic schemas (Action, Observation)
├── inference.py                        # Baseline agent testing script
├── Dockerfile                          # Official Meta OpenEnv BuildKit instructions
├── README.md
└── server/
    ├── app.py                          # OpenEnv FastAPI wrapper
    └── privacy_janitor_environment.py  # Core simulation and dynamic generation logic
```

## 🚀 How to Run

### Via OpenEnv Web Interface

This environment supports the built-in OpenEnv Human-in-the-Loop web UI for manual testing:

1. Navigate to the Hugging Face Space endpoint.
2. Trigger `read_file` and `redact` commands to verify environment behavior.

### Via API (RL Agent)

```python
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
```

