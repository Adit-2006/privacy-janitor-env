import re
import random
from openenv_core.env_server import Environment
from models import PrivacyJanitorAction, PrivacyJanitorObservation

class PrivacyJanitorEnvironment(Environment):
    def __init__(self):
        # Initialize basic attributes to avoid AttributeErrors before first reset
        self.vfs = {}
        self.total_pii_to_find = 0
        self.redacted_pii_count = 0
        self.step_count = 0
        self.task_id = "easy"
        self.episode_id = "initial"
        self.reset()

    def reset(self, task_id: str = "easy", **kwargs):
        """
        Resets the environment for a new episode.
        Supports task_id and arbitrary kwargs (like episode_id from Web UI).
        """
        self.task_id = task_id
        # Capture episode_id if provided by the Web UI or validator
        self.episode_id = kwargs.get("episode_id", f"run_{random.randint(1000, 9999)}")
        
        self.step_count = 0
        self.redacted_pii_count = 0
        self.vfs = {}
        
        # 1. Set the difficulty parameters
        if task_id == "easy":
            num_files = 3
            self.total_pii_to_find = 1
        elif task_id == "medium":
            num_files = 6
            self.total_pii_to_find = 3
        elif task_id == "hard":
            num_files = 12
            self.total_pii_to_find = 5
        else:
            # Default fallback for unknown task_ids
            num_files = 3
            self.total_pii_to_find = 1

        # 2. Build the "Haystack" (Decoy files)
        possible_files = [
            "logs/app.log", "users/data.txt", "readme.md", "src/main.py", 
            "config.json", "secret/db.csv", "temp/cache.tmp", "index.html",
            "assets/logo.svg", "docs/api.md", "tests/test_auth.py", "docker-compose.yml"
        ]
        
        selected_files = random.sample(possible_files, min(num_files, len(possible_files)))
        for f in selected_files:
            self.vfs[f] = f"Standard system file: {f}. Operating within normal parameters."

        # 3. Inject the "Needles" (The PII)
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
        """
        Official score for the leaderboard.
        """
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
                    # Case-insensitive find to be more helpful to the agent
                    matches = len(re.findall(action.pattern, self.vfs[action.path], re.IGNORECASE))
                    if matches > 0:
                        self.vfs[action.path] = re.sub(action.pattern, "[REDACTED]", self.vfs[action.path], flags=re.IGNORECASE)
                        self.redacted_pii_count += matches
                        raw_reward = 0.5 * matches # Individual step reward
                        
                        if self.redacted_pii_count >= self.total_pii_to_find:
                            done = True
                            raw_reward = 1.0 # Completion bonus
                            msg = "Success! All PII has been redacted from the system."
                        else:
                            msg = f"Redacted {matches} instance(s). Total progress: {self.redacted_pii_count}/{self.total_pii_to_find}"
                    else:
                        msg = f"Pattern '{action.pattern}' not found in {action.path}."
                except re.error:
                    msg = "Error: Invalid regex pattern provided."
            else:
                msg = "Error: Invalid file path or missing pattern."

        # Fail-safe termination
        if self.step_count >= 20:
            done = True
            msg += " (Max steps reached)"

        # Apply epsilon clamp to reward for OpenEnv compliance
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
    
    def state(self, **kwargs) -> dict:
        """
        Returns the full internal state for the OpenEnv grader.
        """
        return {
            "task_id": self.task_id,
            "episode_id": self.episode_id,
            "step_count": self.step_count,
            "redacted_count": self.redacted_pii_count,
            "total_to_find": self.total_pii_to_find,
            "files_count": len(self.vfs),
            "vfs_snapshot": self.vfs
        }