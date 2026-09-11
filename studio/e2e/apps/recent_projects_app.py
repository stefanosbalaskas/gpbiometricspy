from __future__ import annotations

import os
from pathlib import Path
import tempfile

# Keep browser validation away from a developer's real Studio history. The app
# subprocess gets a unique local metadata file and the production default path is
# never touched by this fixture.
_recent_store = Path(tempfile.gettempdir()) / f"gpbiometricspy-recent-projects-e2e-{os.getpid()}.json"
try:
    _recent_store.unlink()
except FileNotFoundError:
    pass
os.environ["GPBIOMETRICSPY_STUDIO_RECENT_PROJECTS_PATH"] = str(_recent_store)
os.environ["GPBIOMETRICSPY_STUDIO_MODE"] = "local"

from studio.app import app  # noqa: E402

__all__ = ["app"]
