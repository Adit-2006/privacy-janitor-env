import re
import random
from pydantic import Field
from typing import List, Optional, Literal, Dict, Any, Callable

# Import OpenEnv's base State object
try:
    from openenv.core.env_server import Environment, State
except ImportError:
    from openenv_core.env_server import Environment, State

from models import PrivacyJanitorAction, PrivacyJanitorObservation

# Define a strict typed state for the Grader and Web Interface
class PrivacyJanitorState(State):
    episode_id: str = "initial"
    step_count: int = 0
    task_id: str = "easy"
    redacted_count: int = 0
    total_to_find: int = 0
    files_count: int = 0
    vfs_snapshot: dict = Field(default_factory=dict)

# Robust standalone grader function.
def janitor_grader(state: Any) -> float:
    epsilon = 0.0001
    try:
        if isinstance(state, dict):
            total = state.get("total_to_find", 0)
            redacted = state.get("redacted_count", 0)
        else:
            total = getattr(state, "total_to_find", 0)
            redacted = getattr(state, "redacted_count", 0)

        if total <= 0:
            return float(epsilon)
        
        calculated_score = float(redacted) / float(total)
        return float(max(epsilon, min(1.0 - epsilon, calculated_score)))
    except Exception:
        return float(epsilon)

# Mock Task object to satisfy validator attribute checks
class EnvTask(dict):
    def __init__(self, id: str, name: str, description: str, grader: Callable):
        super().__init__(id=id, name=name, description=description, grader=grader)
        self.id = id
        self.name = name
        self.description = description
        self.grader = grader

class PrivacyJanitorEnvironment(Environment):
    # Class-level tasks list for static inspection
    tasks = [
        EnvTask(id="easy", name="Easy Mode", description="Find 1 PII", grader=janitor_grader),
        EnvTask(id="medium", name="Medium Mode", description="Find 3 PII", grader=janitor_grader),
        EnvTask(id="hard", name="Hard Mode", description="Find 5 PII", grader=janitor_grader)
    ]

    def __init__(self):
        super().__init__()
        self.vfs = {}
        self.total_pii_to_find = 0
        self.redacted_pii_count = 0
        self.step_count = 0
        self.task_id = "easy"
        self.episode_id = "initial"
        self.active_pii = [] # NEW: Track exactly what needs to be found

    def reset(
        self, 
        seed: Optional[int] = None, 
        episode_id: Optional[str] = None, 
        task_id: Literal["easy", "medium", "hard"] = "easy", 
        **kwargs
    ) -> PrivacyJanitorObservation:
        if seed is not None:
            random.seed(seed)
            
        self.task_id = task_id
        self.episode_id = str(episode_id) if episode_id else f"run_{random.randint(1000, 9999)}"
        self.step_count = 0
        self.redacted_pii_count = 0
        self.vfs = {}
        self.active_pii = [] 
        
        config = {"easy": (3, 1), "medium": (6, 3), "hard": (12, 5)}
        num_files, self.total_pii_to_find = config.get(task_id, (3, 1))

        possible_files = ["logs/app.log", "users/data.txt", "readme.md", "src/main.py", "config.json", "secret/db.csv"]
        selected_files = random.sample(possible_files, min(num_files, len(possible_files)))
        
        for f in selected_files:
            self.vfs[f] = f"System file: {f}. Parameters normal."

        domains = ["example.com", "test.org", "company.net", "corp.local"]
        names = ["admin", "john.doe", "jane.smith", "user99", "sysadmin"]
        
        generated_pii = []
        for _ in range(self.total_pii_to_find):
            pii_type = random.choice(["email", "ssn", "card", "phone"])
            if pii_type == "email":
                generated_pii.append(f"{random.choice(names)}@{random.choice(domains)}")
            elif pii_type == "ssn":
                generated_pii.append(f"SSN:{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}")
            elif pii_type == "phone":
                generated_pii.append(f"phone:555-{random.randint(1000,9999)}")
            else:
                generated_pii.append(f"card:4111-{random.randint(1000,9999)}-{random.randint(1000,9999)}")

        # Save exact targets
        self.active_pii = generated_pii.copy()

        for pii in generated_pii:
            target_file = random.choice(list(self.vfs.keys()))
            self.vfs[target_file] += f" [Trace: {pii} recorded]."

        return PrivacyJanitorObservation(
            current_path="/",
            files=list(self.vfs.keys()),
            message=f"Environment reset. Task: {task_id}. Find {self.total_pii_to_find} items.",
            content_preview="Ready.",
            reward=0.0001,
            done=False
        )

    def score(self) -> float:
        return janitor_grader(self.state)

    def step(self, action: PrivacyJanitorAction) -> PrivacyJanitorObservation:
        self.step_count += 1
        raw_reward = 0.0
        done = False
        content_preview = ""
        msg = "Action processed."

        if action.command == "read_file":
            content_preview = self.vfs.get(action.path, "Error: Not found.")
            msg = f"Reading {action.path}"
            
        elif action.command == "redact":
            if action.path in self.vfs and action.pattern:
                try:
                    matches = list(re.finditer(action.pattern, self.vfs[action.path], re.IGNORECASE))
                    if matches:
                        # Nuke exploit check
                        if any(len(m.group(0)) > 50 for m in matches):
                            msg = "CRITICAL ERROR: Pattern too broad. You destroyed non-PII system data!"
                            raw_reward = 0.0001 
                        else:
                            old_text = self.vfs[action.path]
                            new_text = re.sub(action.pattern, "[REDACTED]", old_text, flags=re.IGNORECASE)
                            
                            # --- NEW: STRICT PII VERIFICATION ---
                            # Check exactly how many REAL PII targets were erased by this redaction
                            actual_pii_removed = 0
                            for pii in list(self.active_pii):
                                if pii in old_text and pii not in new_text:
                                    actual_pii_removed += 1
                                    self.active_pii.remove(pii)
                                    
                            if actual_pii_removed > 0:
                                self.vfs[action.path] = new_text
                                self.redacted_pii_count += actual_pii_removed
                                raw_reward = 0.5 * actual_pii_removed
                                
                                if self.redacted_pii_count >= self.total_pii_to_find:
                                    done, raw_reward, msg = True, 1.0, "Success!"
                                else:
                                    msg = f"Progress: {self.redacted_pii_count}/{self.total_pii_to_find}"
                            else:
                                # They redacted innocent text! Reward hacking denied.
                                msg = "Error: You redacted safe text but missed the PII! Check your regex."
                                raw_reward = 0.0001
                            # ------------------------------------
                    else:
                        msg = "Pattern not found."
                except re.error:
                    msg = "Error: Invalid regex pattern."
            else:
                msg = "Invalid path/pattern."
        
        if self.step_count >= 20: done = True

        reward = max(0.0001, min(0.9999, raw_reward))
        return PrivacyJanitorObservation(
            current_path="/", files=list(self.vfs.keys()), 
            content_preview=content_preview, reward=reward, 
            message=msg, done=done
        )
    
    @property
    def state(self) -> PrivacyJanitorState:
        return PrivacyJanitorState(
            episode_id=self.episode_id, step_count=self.step_count, task_id=self.task_id,
            redacted_count=self.redacted_pii_count, total_to_find=self.total_pii_to_find,
            files_count=len(self.vfs), vfs_snapshot=self.vfs
        )   
