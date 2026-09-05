import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_quality_index_numeric_and_mapping_guardrails():
    data = pd.DataFrame({"metric": [1.0, 2.0], "label": ["a", "b"]})

    with pytest.raises(ValueError, match="metric_cols"):
        gp.compute_gazepoint_quality_index(data, [])
    with pytest.raises(ValueError, match="not found"):
        gp.compute_gazepoint_quality_index(data, ["missing"])
    with pytest.raises(TypeError, match="numeric"):
        gp.compute_gazepoint_quality_index(data, ["label"])
    with pytest.raises(ValueError, match="directions"):
        gp.compute_gazepoint_quality_index(data, ["metric"], directions="sideways")
    with pytest.raises(ValueError, match="weights"):
        gp.compute_gazepoint_quality_index(data, ["metric"], weights=-1)


def test_quality_index_collision_and_all_nonfinite_metric():
    collision = pd.DataFrame({"metric": [1.0, 2.0], "quality_index": [0.2, 0.8]})
    with pytest.raises(ValueError, match="already exist"):
        gp.compute_gazepoint_quality_index(collision, ["metric"])

    all_missing = gp.compute_gazepoint_quality_index(
        pd.DataFrame({"metric": [np.nan, np.nan]}), ["metric"]
    )
    assert all_missing["quality_index"].isna().all()
    assert all_missing["quality_component_metric"].isna().all()


def test_beat_audit_public_validation_paths():
    base = pd.DataFrame({"ibi": [800.0, 810.0], "label": ["a", "b"]})

    with pytest.raises(ValueError, match="ibi_col"):
        gp.audit_gazepoint_beats(base, ibi_col="missing")
    with pytest.raises(TypeError, match="numeric"):
        gp.audit_gazepoint_beats(base, ibi_col="label")
    with pytest.raises(ValueError, match="positive"):
        gp.audit_gazepoint_beats(base, ibi_col="ibi", min_ibi=0)
    with pytest.raises(ValueError, match="duplicate_tolerance"):
        gp.audit_gazepoint_beats(base, ibi_col="ibi", duplicate_tolerance=-1)
    with pytest.raises(ValueError, match="max_relative_change"):
        gp.audit_gazepoint_beats(base, ibi_col="ibi", max_relative_change=0)


def test_beat_correction_summary_public_validation_paths():
    with pytest.raises(TypeError, match="correction"):
        gp.summarize_gazepoint_beat_corrections("bad")

    with pytest.raises(ValueError, match="missing required columns"):
        gp.summarize_gazepoint_beat_corrections(pd.DataFrame({"action": ["mask"]}))

    log = pd.DataFrame(
        {
            "action": ["mask"],
            "correction_note": ["masked_flagged_interval"],
            "flag_reason": ["short_ibi"],
            "original_ibi": [100.0],
            "corrected_ibi": [np.nan],
        }
    )
    with pytest.raises(ValueError, match="by"):
        gp.summarize_gazepoint_beat_corrections(log, by="missing")


def test_correct_beats_validation_collision_and_no_reference_fallback():
    with pytest.raises(TypeError, match="audit"):
        gp.correct_gazepoint_beats("bad")

    audit = gp.audit_gazepoint_beats(pd.DataFrame({"ibi": [800.0, 810.0]}), ibi_col="ibi")
    with pytest.raises(ValueError, match="action"):
        gp.correct_gazepoint_beats(audit, action="replace")

    audit_with_collision = gp.audit_gazepoint_beats(
        pd.DataFrame({"ibi": [800.0, 810.0]}), ibi_col="ibi"
    )
    audit_with_collision["beats"]["ibi_corrected"] = audit_with_collision["beats"]["ibi"]
    with pytest.raises(ValueError, match="already exists"):
        gp.correct_gazepoint_beats(audit_with_collision)

    no_reference = gp.correct_gazepoint_beats(
        pd.DataFrame({"ibi": [100.0, 120.0]}),
        action="local_median",
        ibi_col="ibi",
        min_ibi=300,
        max_ibi=2000,
    )
    assert set(no_reference["correction_log"]["correction_note"]) == {
        "masked_no_reference_interval"
    }
    assert no_reference["correction_log"]["corrected_ibi"].isna().all()


def test_session_comparability_public_validation_paths():
    data = pd.DataFrame({"metric": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError, match="method"):
        gp.audit_gazepoint_session_comparability(data, ["metric"], method="mad")
    with pytest.raises(ValueError, match="iqr_multiplier"):
        gp.audit_gazepoint_session_comparability(
            data, ["metric"], iqr_multiplier=-1
        )


def test_qc_overview_public_validation_paths():
    data = pd.DataFrame(
        {
            "quality": ["good", "bad"],
            "flag_text": ["yes", "no"],
            "flag_bool": [True, False],
        }
    )

    with pytest.raises(ValueError, match="quality_index_col"):
        gp.summarize_gazepoint_qc_overview(data, quality_index_col="missing")
    with pytest.raises(TypeError, match="quality_index_col"):
        gp.summarize_gazepoint_qc_overview(data, quality_index_col="quality")
    with pytest.raises(ValueError, match="flag_cols"):
        gp.summarize_gazepoint_qc_overview(data, flag_cols=["missing"])
    with pytest.raises(TypeError, match="flag_cols"):
        gp.summarize_gazepoint_qc_overview(data, flag_cols=["flag_text"])


def test_experiment_design_expected_condition_and_condition_free_paths():
    data = pd.DataFrame({"participant": ["P1", "P1"], "trial": [1, 2]})

    with pytest.raises(ValueError, match="expected_conditions"):
        gp.audit_gazepoint_experiment_design(
            data,
            trial_col="trial",
            expected_conditions=["A", ""],
        )

    out = gp.audit_gazepoint_experiment_design(data, trial_col="trial")
    assert out["condition_summary"].empty
    assert out["participant_condition_counts"].empty
    assert not bool(out["overview"].loc[0, "has_condition_column"])


def test_design_coverage_plot_requires_audit_object():
    with pytest.raises(TypeError, match="audit"):
        gp.plot_gazepoint_design_coverage(pd.DataFrame({"x": [1]}))
