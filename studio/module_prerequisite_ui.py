from __future__ import annotations

from shiny import module, ui


@module.ui
def module_readiness_ui():
    """Render the advisory readiness output inside its own Shiny namespace."""
    return ui.output_ui("module_readiness")
