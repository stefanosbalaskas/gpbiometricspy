from __future__ import annotations

from dataclasses import dataclass
from os import environ
from typing import Mapping

STUDIO_MODE_ENV = "GPBIOMETRICSPY_STUDIO_MODE"
LOCAL_MODE = "local"
PUBLIC_DEMO_MODE = "public-demo"
VALID_MODES = frozenset({LOCAL_MODE, PUBLIC_DEMO_MODE})

PUBLIC_UPLOAD_BLOCK_MESSAGE = (
    "External file uploads are disabled in the public gpbiometricspy Studio demonstration. "
    "Run studio/app.py locally or deploy the authenticated full Studio when working with research data."
)


@dataclass(frozen=True)
class StudioRuntimeConfig:
    """Runtime policy for the interactive Studio layer."""

    mode: str = LOCAL_MODE

    @property
    def is_public_demo(self) -> bool:
        return self.mode == PUBLIC_DEMO_MODE

    @property
    def allow_external_uploads(self) -> bool:
        return not self.is_public_demo

    @property
    def sanitize_errors(self) -> bool:
        return self.is_public_demo

    @property
    def mode_label(self) -> str:
        return "Public synthetic demonstration" if self.is_public_demo else "Local / controlled Studio"


def studio_runtime_config(env: Mapping[str, str] | None = None) -> StudioRuntimeConfig:
    """Resolve Studio runtime policy from the environment and reject unknown modes."""
    values = environ if env is None else env
    mode = str(values.get(STUDIO_MODE_ENV, LOCAL_MODE)).strip().lower() or LOCAL_MODE
    if mode not in VALID_MODES:
        allowed = ", ".join(sorted(VALID_MODES))
        raise ValueError(f"Unsupported {STUDIO_MODE_ENV}={mode!r}. Allowed values: {allowed}.")
    return StudioRuntimeConfig(mode=mode)


def reject_external_upload(label: str = "External file upload") -> None:
    """Fail closed when a public-demo code path attempts to consume an uploaded file."""
    raise PermissionError(f"{label} blocked. {PUBLIC_UPLOAD_BLOCK_MESSAGE}")
