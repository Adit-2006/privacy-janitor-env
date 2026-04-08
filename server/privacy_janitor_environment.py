import re
import random
from pydantic import Field
from typing import List, Optional, Literal, Dict, Any

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

class PrivacyJanitorEnvironment(Environment):
    def __init__(self):
        super().__init__() # Good practice to initialize the parent class
        self.vfs = {}
        self.total_pii_to_find = 0
        self.redacted_pii_count = 0
        self.step_count = 0
        self.task_id = "easy"
        self.episode_id = "initial"

    # FIX: Shifted reset() to the left so it's a proper class method
    def reset(
        self, 
        seed: Optional[int] = None, 
        episode_id: Optional[str] = None, 
        task_id: Literal["easy", "medium", "hard"] = "easy", 
        **kwargs
    ) -> PrivacyJanitorObservation:
        # FIX: Indented the logic inside the reset function correctly
        if seed is not None:
            random.seed(seed)
            
        self.task_id = task_id
        self.episode_id = str(episode_id) if episode_id else f"run_{random.randint(1000, 9999)}"
        
        self.step_count = 0
        self.redacted_pii_count = 0
        self.vfs = {}
        
        if task_id == "easy":
            num_files, self.total_pii_to_find = 3, 1
        elif task_id == "medium":
            num_files, self.total_pii_to_find = 6, 3
        elif task_id == "hard":
            num_files, self.total_pii_to_find = 12, 5
        else:
            num_files, self.total_pii_to_find = 3, 1

        possible_files = [
            "logs/app.log", "users/data.txt", "readme.md", "src/main.py", 
            "config.json", "secret/db.csv", "temp/cache.tmp", "index.html",
            "assets/logo.svg", "docs/api.md", "tests/test_auth.py", "docker-compose.yml"
        ]
        
        selected_files = random.sample(possible_files, min(num_files, len(possible_files)))
        for f in selected_files:
            self.vfs[f] = f"Standard system file: {f}. Operating within normal parameters."

        pii_pool = [
            "admin@example.com", "john@doe.com", "phone:555-0199", 
            "jane@smith.com", "card:4111-2222", "SSN:000-00-0000"
        ]
        
        selected_pii = random.sample(pii_pool, min(self.total_pii_to_find, len(pii_pool)))

        for pii in selected_pii:
            target_file = random.choice(list(self.vfs.keys()))
            self.vfs[target_file] += f" [System trace: {pii} recorded in buffer]."

        return PrivacyJanitorObservation(
            current_path="/",
            files=list(self.vfs.keys()),
            message=f"Environment reset. Task: {task_id}. Find and redact {self.total_pii_to_find} PII items.",
            content_preview="Enter a file path and use 'read_file' to begin.",
            reward=0.0001,
            done=False
        )

    def score(self) -> float:
        epsilon = 0.0001
        if self.total_pii_to_find <= 0:
            return float(epsilon)
        calculated_score = float(self.redacted_pii_count) / self.total_pii_to_find
        final_score = max(epsilon, min(1.0 - epsilon, calculated_score))
        return float(final_score)

    def step(self, action: PrivacyJanitorAction) -> PrivacyJanitorObservation:
        self.step_count += 1
        raw_reward = 0.0
        msg = "Action processed."
        done = False
        content_preview = ""

        if action.command == "read_file":
            content_preview = self.vfs.get(action.path, "Error: File not found.")
            msg = f"Reading content of {action.path}"

        elif action.command == "redact":
            if action.path in self.vfs and action.pattern:
                try:
                    matches = len(re.findall(action.pattern, self.vfs[action.path], re.IGNORECASE))
                    if matches > 0:
                        self.vfs[action.path] = re.sub(action.pattern, "[REDACTED]", self.vfs[action.path], flags=re.IGNORECASE)
                        self.redacted_pii_count += matches
                        raw_reward = 0.5 * matches
                        
                        if self.redacted_pii_count >= self.total_pii_to_find:
                            done = True
                            raw_reward = 1.0
                            msg = "Success! All PII has been redacted."
                        else:
                            msg = f"Redacted {matches} instance(s). Progress: {self.redacted_pii_count}/{self.total_pii_to_find}"
                    else:
                        msg = f"Pattern '{action.pattern}' not found in {action.path}."
                except re.error:
                    msg = "Error: Invalid regex pattern."
            else:
                msg = "Error: Invalid path or pattern."

        if self.step_count >= 20:
            done = True
            msg += " (Max steps reached)"

        epsilon = 0.0001
        clamped_reward = max(epsilon, min(1.0 - epsilon, raw_reward))

        return PrivacyJanitorObservation(
            current_path="/", 
            files=list(self.vfs.keys()), 
            content_preview=content_preview,
            reward=clamped_reward,
            message=msg,
            done=done
        )
    
    @property
    def state(self) -> PrivacyJanitorState:
        return PrivacyJanitorState(
            episode_id=self.episode_id,
            step_count=self.step_count,
            task_id=self.task_id,
            redacted_count=self.redacted_pii_count,
            total_to_find=self.total_pii_to_find,
            files_count=len(self.vfs),
            vfs_snapshot=self.vfs
        )
