# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""
FastAPI application for the Privacy Janitor Environment.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field

try:
    from openenv.core.env_server.http_server import create_app
except ImportError as e:
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

from models import PrivacyJanitorAction, PrivacyJanitorObservation
from server.privacy_janitor_environment import PrivacyJanitorEnvironment

# Pass the classes into the app creator (Removed the unsupported schema argument)
app = create_app(
    PrivacyJanitorEnvironment,
    PrivacyJanitorAction,
    PrivacyJanitorObservation,
    env_name="privacy_janitor",
    max_concurrent_envs=1,
)

def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
