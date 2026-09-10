"""Reusable Shiny modules for gpbiometricspy Studio.

The product shell adds a compact readiness banner to the major Analyze and
Integrate workflows at this package boundary. Scientific module files remain
unchanged; readiness is advisory and is derived from their existing service
helpers and shared ProjectState.
"""

from __future__ import annotations

from functools import wraps
from types import ModuleType
from typing import Any, Callable

from shiny import ui

try:
    from studio.module_prerequisite_runtime import module_readiness_runtime_server
    from studio.module_prerequisite_ui import module_readiness_ui
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from module_prerequisite_runtime import module_readiness_runtime_server
    from module_prerequisite_ui import module_readiness_ui


def _wrap_with_readiness(
    module_obj: ModuleType,
    *,
    ui_name: str,
    server_name: str,
    module_key: str,
) -> None:
    """Attach one advisory readiness module without altering scientific logic."""

    marker = f"_studio_readiness_wrapped_{module_key}"
    if getattr(module_obj, marker, False):
        return

    original_ui: Callable[..., Any] = getattr(module_obj, ui_name)
    original_server: Callable[..., Any] = getattr(module_obj, server_name)

    @wraps(original_ui)
    def wrapped_ui(module_id: str, *args: Any, **kwargs: Any):
        readiness_id = f"{module_id}_readiness"
        return ui.TagList(
            module_readiness_ui(readiness_id),
            original_ui(module_id, *args, **kwargs),
        )

    @wraps(original_server)
    def wrapped_server(
        module_id: str,
        state: Any,
        status_text: Any,
        *args: Any,
        **kwargs: Any,
    ):
        result = original_server(module_id, state, status_text, *args, **kwargs)
        module_readiness_runtime_server(f"{module_id}_readiness", state, module_key)
        return result

    setattr(module_obj, ui_name, wrapped_ui)
    setattr(module_obj, server_name, wrapped_server)
    setattr(module_obj, marker, True)


# Import and wrap only the workflows whose prerequisites can be resolved from
# existing Studio capability services. QC, annotation, statistics/modelling and
# reporting retain their native interfaces.
from . import eda_scr as _eda_scr  # noqa: E402
from . import event_alignment as _event_alignment  # noqa: E402
from . import gaze as _gaze  # noqa: E402
from . import multimodal as _multimodal  # noqa: E402
from . import ppg_hr_hrv as _ppg_hr_hrv  # noqa: E402
from . import pupil as _pupil  # noqa: E402

_wrap_with_readiness(
    _eda_scr,
    ui_name="eda_scr_ui",
    server_name="eda_scr_server",
    module_key="eda_scr",
)
_wrap_with_readiness(
    _ppg_hr_hrv,
    ui_name="ppg_hr_hrv_ui",
    server_name="ppg_hr_hrv_server",
    module_key="ppg_hr_hrv",
)
_wrap_with_readiness(
    _pupil,
    ui_name="pupil_ui",
    server_name="pupil_server",
    module_key="pupil",
)
_wrap_with_readiness(
    _gaze,
    ui_name="gaze_ui",
    server_name="gaze_server",
    module_key="gaze",
)
_wrap_with_readiness(
    _event_alignment,
    ui_name="event_alignment_ui",
    server_name="event_alignment_server",
    module_key="event_alignment",
)
_wrap_with_readiness(
    _multimodal,
    ui_name="multimodal_ui",
    server_name="multimodal_server",
    module_key="multimodal",
)
