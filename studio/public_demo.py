from __future__ import annotations

import os
from typing import Any

from studio.config import PUBLIC_DEMO_MODE, STUDIO_MODE_ENV, reject_external_upload

# This module is the public deployment boundary. Force the safest runtime policy
# before importing the full Studio so its UI is rendered in public-demo mode.
os.environ[STUDIO_MODE_ENV] = PUBLIC_DEMO_MODE

import studio.app as studio_app  # noqa: E402
from studio.modules import event_alignment, gaze, reporting  # noqa: E402


def _block_biometrics_upload(_file_info: Any) -> None:
    reject_external_upload("Gazepoint biometric dataset upload")


def _block_aoi_upload(_file_info: Any) -> None:
    reject_external_upload("AOI definition upload")


def _block_event_log_upload(_file_info: Any) -> None:
    reject_external_upload("External event-log upload")


def _block_target_stream_upload(_file_info: Any) -> None:
    reject_external_upload("Secondary biometric stream upload")


def _block_recipe_upload(_file_info: Any) -> None:
    reject_external_upload("Project-recipe upload")


# Server-side guardrails complement the public UI. Even if a client attempts to
# synthesize Shiny input messages manually, external file consumers fail closed.
studio_app.load_uploaded_dataset = _block_biometrics_upload
gaze.load_aoi_definitions = _block_aoi_upload
event_alignment.load_event_log = _block_event_log_upload
event_alignment.load_target_stream = _block_target_stream_upload
reporting.load_project_recipe_upload = _block_recipe_upload

app = studio_app.app
app.sanitize_errors = True

__all__ = ["app"]
