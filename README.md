---
title: Privacy Janitor Environment
emoji: 🧹
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 🧹 Privacy Janitor Environment

**A Meta OpenEnv Hackathon Submission**

Privacy Janitor is a lightweight, dynamically-generating reinforcement learning environment built strictly to the OpenEnv specification. The goal of the AI agent is to navigate a virtual file system, locate hidden Personally Identifiable Information (PII) like email addresses, and successfully redact them using strict JSON commands.

## 🚀 Architecture & Compliance Highlights

This submission was explicitly engineered to pass all automated OpenEnv grading requirements:
- **Dynamic Task Generation:** Implements 3 distinct difficulty tiers (`easy`, `medium`, `hard`) using procedural generation to prevent model memorization.
- **Strict Grader Compliance:** The `score()` endpoint mathematically tracks PII redaction, returning a strict `0.0` to `1.0` float, allowing for partial credit.
- **Infrastructure Optimized:** Offloads LLM inference to the Hugging Face Router via the OpenAI SDK, ensuring the local footprint remains well under the 2vCPU / 8GB memory limits. Total inference time is < 30 seconds.
- **OpenEnv Spec:** Fully implements `reset()`, `step()`, and the required `state()` endpoints wrapped in a FastAPI server.
- **Modern Docker Build:** Utilizes a multi-stage BuildKit Dockerfile with `--mount=type=cache` and `uv` for lightning-fast container compilation.

## 📁 Repository Structure

```text
privacy_janitor/
├── openenv.yaml                # OpenEnv configuration and FastAPI entrypoint
├── models.py                   # Pydantic schemas (Action, Observation, EnvState)
├── inference.py                # Baseline agent testing script
├── verify_graders.py           # Mathematical validation suite for the scoring logic
├── README.md                   
└── server/
    ├── app.py                  # OpenEnv FastAPI wrapper
    ├── Dockerfile              # Official Meta OpenEnv BuildKit instructions
    └── privacy_janitor_environment.py # Core simulation and dynamic generation logic