from typing import List, Optional, Literal # Added Literal
from pydantic import BaseModel, Field

class PrivacyJanitorAction(BaseModel):
    # Change str to Literal here
    command: Literal["read_file", "redact"] = Field(..., description="The command to execute")
    path: str = Field(..., description="The target file path (e.g. 'logs/app.log')")
    pattern: Optional[str] = Field(default=None, description="The regex pattern to apply")

class PrivacyJanitorObservation(BaseModel):
    current_path: str = Field(default="/", description="Current directory of the agent")
    files: List[str] = Field(default_factory=list, description="Files available in the system")
    message: str = Field(default="", description="System feedback from the last action")
    content_preview: str = Field(default="", description="File contents if read_file was used")
    
    # RL Mandatory Fields
    reward: float = Field(default=0.0001, description="The current reward of the environment")
    done: bool = Field(default=False, description="Whether the episode has finished")

class EnvState(BaseModel):
    task_id: str
    step_count: int
    files_in_system: int
