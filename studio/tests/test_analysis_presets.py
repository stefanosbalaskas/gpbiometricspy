from __future__ import annotations

import pytest

from studio.analysis_presets import (
    SUPPORTED_PRESET_MODULES,
    analysis_presets,
    preset_by_key,
    presets_for_module,
    teaching_routes,
)


def test_presets_cover_supported_analysis_and_integration_destinations():
    assert SUPPORTED_PRESET_MODULES == {
        "eda_scr",
        "ppg_hr_hrv",
        "pupil",
        "gaze",
        "event_alignment",
        "multimodal",
        "statistics_modelling",
    }
    presets = analysis_presets()
    assert len(presets) == 8
    assert len({preset.key for preset in presets}) == len(presets)
    for module_key in SUPPORTED_PRESET_MODULES:
        assert presets_for_module(module_key)


def test_every_preset_is_complete_advisory_and_guardrailed():
    for preset in analysis_presets():
        assert preset.key
        assert preset.label
        assert preset.goal
        assert preset.guided_defaults
        assert preset.prerequisites
        assert preset.verify_before_inference
        assert preset.next_step
        assert preset.guardrail
        assert any(token in preset.guardrail.lower() for token in ("not", "does not"))
        assert all(isinstance(value, str) and value.strip() for value in preset.guided_defaults)
        assert all(isinstance(value, str) and value.strip() for value in preset.prerequisites)
        assert all(isinstance(value, str) and value.strip() for value in preset.verify_before_inference)


def test_documented_guided_values_match_existing_visible_module_defaults():
    eda = preset_by_key("eda-foundations")
    cardiac = preset_by_key("cardiac-foundations")
    pupil = preset_by_key("pupil-foundations")
    gaze = preset_by_key("gaze-foundations")
    alignment = preset_by_key("event-alignment-foundations")
    multimodal = preset_by_key("multimodal-foundations")
    cluster = preset_by_key("cluster-permutation-foundations")

    assert "Tonic window: 31 samples" in eda.guided_defaults
    assert "RR rejection tolerance: 0.30" in cardiac.guided_defaults
    assert "No interpolation" in pupil.guided_defaults
    assert "Minimum fixation: 100 ms; minimum saccade: 10 ms" in gaze.guided_defaults
    assert "Pre-event window: 1.0 s; post-event window: 5.0 s" in alignment.guided_defaults
    assert "Baseline window: -1.0 to 0.0 s; summary window: 0.0 to 3.0 s" in multimodal.guided_defaults
    assert "Permutations: 1000; cluster-forming alpha: 0.05; cluster alpha: 0.05" in cluster.guided_defaults


def test_cluster_preset_preserves_validated_design_boundary():
    cluster = preset_by_key("cluster-permutation-foundations")
    combined = " ".join(
        (
            cluster.goal,
            *cluster.prerequisites,
            *cluster.verify_before_inference,
            cluster.guardrail,
        )
    ).lower()
    assert "two-condition" in combined or "two conditions" in combined
    assert "within-subject" in combined
    assert "one-dimensional" in combined
    assert "design diagnostics" in combined
    assert "precise" in combined and "onset" in combined


def test_model_preparation_never_claims_a_fitted_model():
    model = preset_by_key("model-preparation-foundations")
    text = " ".join((model.goal, *model.verify_before_inference, model.guardrail)).lower()
    assert "not" in text
    assert "fitted model" in text or "model was fitted" in text


def test_teaching_routes_cover_existing_guided_families_plus_modelling():
    routes = teaching_routes()
    assert [route.key for route in routes] == [
        "physiology",
        "eye_tracking",
        "multimodal",
        "modelling",
    ]
    for route in routes:
        assert len(route.route) >= 4
        assert route.goal
        assert route.evidence_focus
        assert route.stop_and_check
        assert "report" in " ".join(route.route).lower()


def test_unknown_preset_and_module_fail_closed():
    with pytest.raises(ValueError, match="Unknown Studio analysis preset"):
        preset_by_key("not-a-preset")
    with pytest.raises(ValueError, match="Unsupported Studio preset module"):
        presets_for_module("not-a-module")
