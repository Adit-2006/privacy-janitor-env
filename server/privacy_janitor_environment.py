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

# FIX: Robust standalone grader function.
# The validator may pass a dictionary or a state object; this handles both.
def janitor_grader(state: Any) -> float:
    epsilon = 0.0001
    try:
        # Extract data regardless of whether 'state' is a dict or an object
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

# FIX: Mock Task object to satisfy validator attribute checks
class EnvTask(dict):
    def __init__(self, id: str, name: str, description: str, grader: Callable):
        super().__init__(id=id, name=name, description=description, grader=grader)
        self.id = id
        self.name = name
        self.description = description
        self.grader = grader

class PrivacyJanitorEnvironment(Environment):
    # THE FIX: Class-level tasks list for static inspection
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
        
        config = {"easy": (3, 1), "medium": (6, 3), "hard": (12, 5)}
        num_files, self.total_pii_to_find = config.get(task_id, (3, 1))

        possible_files = ["logs/app.log", "users/data.txt", "readme.md", "src/main.py", "config.json", "secret/db.csv"]
        selected_files = random.sample(possible_files, min(num_files, len(possible_files)))
        
        for f in selected_files:
            self.vfs[f] = f"System file: {f}. Parameters normal."

        pii_pool = ["admin@example.com", "phone:555-0199", "SSN:000-00-0000"]
        selected_pii = random.sample(pii_pool, min(self.total_pii_to_find, len(pii_pool)))

        for pii in selected_pii:
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

        if action.command == "read_file":
            content_preview = self.vfs.get(action.path, "Error: Not found.")
            msg = f"Reading {action.path}"
        elif action.command == "redact":
            if action.path in self.vfs and action.pattern:
                matches = len(re.findall(action.pattern, self.vfs[action.path], re.IGNORECASE))
                if matches > 0:
                    self.vfs[action.path] = re.sub(action.pattern, "[REDACTED]", self.vfs[action.path], flags=re.IGNORECASE)
                    self.redacted_pii_count += matches
                    raw_reward = 0.5 * matches
                    if self.redacted_pii_count >= self.total_pii_to_find:
                        done, raw_reward, msg = True, 1.0, "Success!"
                    else:
                        msg = f"Progress: {self.redacted_pii_count}/{self.total_pii_to_find}"
                else:
                    msg = "Pattern not found."
            else:
                msg = "Invalid path/pattern."
        
        if self.step_count >= 20: done = True

        reward = max(0.0001, min(0.9999, raw_reward))
        return PrivacyJanitorObservation(
            current_path="/", files=list(self.vfs.keys()), 
            content_preview=content_preview, reward=reward, 
            message=msg if 'msg' in locals() else "Step processed.", done=done
        )
    
    @property
    def state(self) -> PrivacyJanitorState:
        return PrivacyJanitorState(
            episode_id=self.episode_id, step_count=self.step_count, task_id=self.task_id,
            redacted_count=self.redacted_pii_count, total_to_find=self.total_pii_to_find,
            files_count=len(self.vfs), vfs_snapshot=self.vfs
        )
