from __future__ import annotations

from shiny import module, ui

try:
    from studio.analysis_presets import presets_for_module, teaching_routes
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from analysis_presets import presets_for_module, teaching_routes


def _joined(values: tuple[str, ...]) -> str:
    return " · ".join(values)


@module.ui
def analysis_preset_ui(module_key: str):
    """Render static preset guidance without mutating any scientific input."""

    presets = presets_for_module(module_key)
    blocks = []
    for preset in presets:
        blocks.append(
            ui.div(
                ui.tags.strong(preset.label),
                ui.p(preset.goal, class_="mb-2"),
                ui.tags.small(
                    ui.tags.strong("Guided baseline: "),
                    _joined(preset.guided_defaults),
                    class_="d-block text-secondary mb-2",
                ),
                ui.tags.small(
                    ui.tags.strong("Prerequisites: "),
                    _joined(preset.prerequisites),
                    class_="d-block text-secondary mb-2",
                ),
                ui.tags.small(
                    ui.tags.strong("Before inference: "),
                    _joined(preset.verify_before_inference),
                    class_="d-block text-secondary mb-2",
                ),
                ui.tags.small(
                    ui.tags.strong("Guardrail: "),
                    preset.guardrail,
                    class_="d-block text-secondary mb-2",
                ),
                ui.tags.small(
                    ui.tags.strong("Next: "),
                    preset.next_step,
                    class_="d-block text-secondary",
                ),
                class_="mb-3",
                data_preset_key=preset.key,
            )
        )
    return ui.card(
        ui.card_header("Teaching preset guidance"),
        ui.p(
            "Advisory only. These cards document the current Guided-mode starting point; they do not change controls, run analyses, or replace protocol-specific decisions.",
            class_="small mb-3",
        ),
        *blocks,
        class_="studio-preset-guidance",
    )


def teaching_routes_ui():
    """Render static Home teaching narratives across existing workflows."""

    cards = []
    for route in teaching_routes():
        cards.append(
            ui.card(
                ui.card_header(route.label),
                ui.p(route.goal),
                ui.tags.small(
                    ui.tags.strong("Route: "),
                    " → ".join(route.route),
                    class_="d-block text-secondary mb-2",
                ),
                ui.tags.small(
                    ui.tags.strong("Evidence focus: "),
                    route.evidence_focus,
                    class_="d-block text-secondary mb-2",
                ),
                ui.tags.small(
                    ui.tags.strong("Stop and check: "),
                    route.stop_and_check,
                    class_="d-block text-secondary",
                ),
                class_="studio-teaching-route",
                data_route_key=route.key,
            )
        )
    return ui.div(
        ui.h4("Teaching routes", class_="mb-1"),
        ui.p(
            "Use these narratives to learn why the steps are ordered this way. They are not automated analysis pipelines.",
            class_="text-secondary mb-3",
        ),
        ui.layout_column_wrap(*cards, width=1 / 2),
        class_="studio-teaching-routes",
    )
