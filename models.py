from typing import List, Optional
from pydantic import BaseModel

class Action(BaseModel):
    command: str
    path: str
    pattern: Optional[str] = None

class Observation(BaseModel):
    # Use colons (:) to define the type, followed by equals (=) for the default value
    current_path: str = "/"
    files: List[str] = []
    message: str = ""
    content_preview: str = ""
    reward_signal: float = 0.0
    done: bool = False

class EnvState(BaseModel):
    task_id: str
    step_count: int
    files_in_system: int