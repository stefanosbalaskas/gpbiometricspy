"""Reusable Shiny modules for gpbiometricspy Studio.

The product shell adds compact readiness and teaching-preset guidance at this
package boundary. Scientific module files remain unchanged; both layers are
advisory and reuse established Studio capability/default contracts.
"""

from __future__ import annotations

from functools import wraps
from types import ModuleType
from typing import Any, Callable

from shiny import ui

try:
    from studio.analysis_preset_ui import analysis_preset_ui
    from studio.module_prerequisite_runtime import module_readiness_runtime_server
    from studio.module_prerequisite_ui import module_readiness_ui
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from analysis_preset_ui import analysis_preset_ui
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


def _wrap_with_preset_guidance(
    module_obj: ModuleType,
    *,
    ui_name: str,
    module_key: str,
) -> None:
    """Attach static teaching guidance without changing controls or server state."""

    marker = f"_studio_preset_wrapped_{module_key}"
    if getattr(module_obj, marker, False):
        return

    original_ui: Callable[..., Any] = getattr(module_obj, ui_name)

    @wraps(original_ui)
    def wrapped_ui(module_id: str, *args: Any, **kwargs: Any):
        return ui.TagList(
            analysis_preset_ui(f"{module_id}_preset", module_key=module_key),
            original_ui(module_id, *args, **kwargs),
        )

    setattr(module_obj, ui_name, wrapped_ui)
    setattr(module_obj, marker, True)


# Import and wrap only workflows with documented product guidance. Readiness is
# attached to modules whose prerequisites can be resolved from existing Studio
# capability services. Preset guidance is static and may also document the Model
# workspace without adding a readiness or scientific execution path.
from . import eda_scr as _eda_scr  # noqa: E402
from . import event_alignment as _event_alignment  # noqa: E402
from . import gaze as _gaze  # noqa: E402
from . import multimodal as _multimodal  # noqa: E402
from . import ppg_hr_hrv as _ppg_hr_hrv  # noqa: E402
from . import pupil as _pupil  # noqa: E402
from . import statistics_modelling as _statistics_modelling  # noqa: E402

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

for _module, _ui_name, _module_key in (
    (_eda_scr, "eda_scr_ui", "eda_scr"),
    (_ppg_hr_hrv, "ppg_hr_hrv_ui", "ppg_hr_hrv"),
    (_pupil, "pupil_ui", "pupil"),
    (_gaze, "gaze_ui", "gaze"),
    (_event_alignment, "event_alignment_ui", "event_alignment"),
    (_multimodal, "multimodal_ui", "multimodal"),
    (_statistics_modelling, "statistics_modelling_ui", "statistics_modelling"),
):
    _wrap_with_preset_guidance(_module, ui_name=_ui_name, module_key=_module_key)
