from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def _rectangles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "aoi": ["large", "small"],
            "xmin": [0.0, 0.25],
            "xmax": [1.0, 0.75],
            "ymin": [0.0, 0.25],
            "ymax": [1.0, 0.75],
            "priority": [2, 1],
        }
    )


def test_aoi_public_validation_overwrite_and_overlap_paths():
    defs = _rectangles()

    with pytest.raises(ValueError, match="detect gaze x/y"):
        gp.assign_gazepoint_aoi(pd.DataFrame({"z": [0.5]}), defs)
    with pytest.raises(ValueError, match="must be numeric"):
        gp.assign_gazepoint_aoi(
            pd.DataFrame({"gaze_x": ["bad"], "gaze_y": [0.5]}), defs
        )
    with pytest.raises(ValueError, match="was not found in `aois`"):
        gp.assign_gazepoint_aoi(
            pd.DataFrame({"gaze_x": [0.5], "gaze_y": [0.5]}),
            defs.drop(columns="aoi"),
        )

    existing = pd.DataFrame({"gaze_x": [0.1], "gaze_y": [0.1], "AOI": ["old"]})
    with pytest.raises(ValueError, match="already exists"):
        gp.assign_gazepoint_aoi(existing, defs)
    replaced = gp.assign_gazepoint_aoi(existing, defs, overwrite=True)
    assert replaced.AOI.tolist() == ["large"]

    with pytest.raises(ValueError, match="equal length"):
        gp.assign_gazepoint_aoi(
            pd.DataFrame({"gaze_x": [0.5], "gaze_y": [0.5], "scene": ["A"]}),
            defs.assign(scene="A"),
            data_match_cols=["scene"],
            aoi_match_cols=[],
        )
    with pytest.raises(ValueError, match="Missing rectangle columns"):
        gp.assign_gazepoint_aoi(
            pd.DataFrame({"gaze_x": [0.5], "gaze_y": [0.5]}),
            pd.DataFrame({"aoi": ["A"], "xmin": [0.0]}),
            format="rectangle",
        )
    with pytest.raises(ValueError, match="aoi_id_col"):
        gp.assign_gazepoint_aoi(
            pd.DataFrame({"gaze_x": [0.5], "gaze_y": [0.5]}),
            pd.DataFrame(
                {
                    "aoi": ["P", "P", "P"],
                    "vertex_x": [0.0, 1.0, 0.0],
                    "vertex_y": [0.0, 0.0, 1.0],
                }
            ),
            format="polygon",
        )

    gaze = pd.DataFrame({"gaze_x": [0.5], "gaze_y": [0.5]})
    with pytest.raises(ValueError, match="Multiple AOIs"):
        gp.assign_gazepoint_aoi(gaze, defs, overlap="error")
    all_hits = gp.assign_gazepoint_aoi(gaze, defs, overlap="all", all_separator="+")
    assert all_hits.AOI.iloc[0] == "large+small"
    smallest = gp.assign_gazepoint_aoi(gaze, defs, overlap="smallest")
    assert smallest.AOI.iloc[0] == "small"

    boundary = gp.assign_gazepoint_aoi(
        pd.DataFrame({"gaze_x": [0.0], "gaze_y": [0.5]}),
        defs.iloc[[0]],
        boundary="outside",
    )
    assert boundary.aoi_assignment_status.iloc[0] == "unmatched"


def test_preregistration_and_trial_regressor_guardrails(tmp_path):
    with pytest.raises(ValueError, match="signal_standardization"):
        gp.create_gazepoint_preregistration_template(signal_standardization="bad")
    with pytest.raises(ValueError, match="artifact_rules"):
        gp.create_gazepoint_preregistration_template(artifact_rules="bad")

    out = tmp_path / "prereg.md"
    text = gp.create_gazepoint_preregistration_template(
        signal_standardization="none", artifact_rules="custom", output_file=out
    )
    assert out.read_text(encoding="utf-8") == text

    with pytest.raises(ValueError, match="detect time column"):
        gp.create_gazepoint_trial_regressors(pd.DataFrame({"signal": [1.0]}), [0.0])
    with pytest.raises(ValueError, match="detect event time column"):
        gp.create_gazepoint_trial_regressors(
            pd.DataFrame({"time": [0.0], "signal": [1.0]}),
            pd.DataFrame({"condition": ["A"]}),
            time_col="time",
        )

    data = pd.DataFrame(
        {
            "participant": ["P1", "P1", "P2", "P2"],
            "time": [0.0, 1.0, 0.0, 1.0],
            "signal": [1.0, 3.0, 10.0, 14.0],
        }
    )
    design = pd.DataFrame(
        {
            "onset": [0.5, 0.5],
            "event": ["e1", "e2"],
            "participant": ["P1", "P2"],
            "condition": ["A", "B"],
        }
    )
    trials = gp.create_gazepoint_trial_regressors(
        data,
        design,
        pre=0.5,
        post=0.5,
        time_col="time",
        event_time_col="onset",
        event_id_col="event",
        signal_cols="signal",
        subject_col="participant",
        design_subject_col="participant",
        carry_design_cols="condition",
    )
    assert trials.trial_id.tolist() == ["e1", "e2"]
    assert trials.signal_mean.tolist() == [2.0, 12.0]


def test_bids_export_auto_seconds_write_and_overwrite_guard(tmp_path):
    with pytest.raises(ValueError, match="detect timestamp"):
        gp.export_gazepoint_to_bids(
            pd.DataFrame({"value": [1.0]}), tmp_path / "missing", "01", "task"
        )

    gaze = pd.DataFrame(
        {
            "time_s": [0.0, 0.1, 0.2],
            "gaze_x": [0.1, 0.2, 0.3],
            "gaze_y": [0.2, 0.3, 0.4],
            "pupil": [3.0, 3.1, 3.2],
        }
    )
    root = tmp_path / "bids"
    written = gp.export_gazepoint_to_bids(
        gaze,
        root,
        "01",
        "read",
        timestamp_units="auto",
        dataset_name="Synthetic gaze",
    )
    assert written["settings"]["timestamp_units"] == "seconds"
    assert written["audit"]["ready_to_write"]

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        gp.export_gazepoint_to_bids(gaze, root, "01", "read")

    overwritten = gp.export_gazepoint_to_bids(
        gaze, root, "01", "read", overwrite=True, include_pupil=False
    )
    assert "pupil_size" not in overwritten["data"]


def test_adapter_public_missing_irregular_aoi_and_duplicate_paths():
    with pytest.raises(ValueError, match="participant/trial"):
        gp.prepare_gazepoint_eyetrackingr_input(
            pd.DataFrame({"trial": ["T"], "time_s": [0.0]})
        )

    categorical = pd.DataFrame(
        {
            "participant": ["P1"] * 3,
            "trial": ["T1"] * 3,
            "time_s": [0.0, 0.1, 0.2],
            "gaze_x": [0.1, 0.2, 0.3],
            "gaze_y": [0.2, 0.3, 0.4],
            "AOI": ["target", "outside", None],
        }
    )
    eye = gp.prepare_gazepoint_eyetrackingr_input(
        categorical, aoi_col="AOI", treat_non_aoi_looks_as_missing=False
    )
    assert "target" in eye["data"].columns
    assert eye["row_audit"].non_aoi_look.tolist() == [False, True, True]

    irregular = pd.DataFrame(
        {
            "participant": ["P1"] * 3,
            "trial": ["T1"] * 3,
            "time_s": [0.0, 0.1, 0.25],
            "gaze_x": [0.1, 0.2, 0.3],
            "gaze_y": [0.2, 0.3, 0.4],
        }
    )
    with pytest.raises(ValueError, match="Irregular"):
        gp.prepare_gazepoint_gazer_input(irregular)
    with pytest.raises(ValueError, match="Irregular"):
        gp.prepare_gazepoint_pupillometryr_input(
            irregular.assign(pupil=[3.0, 3.1, 3.2])
        )

    duplicate = pd.DataFrame(
        {
            "participant": ["P1", "P1"],
            "trial": ["T1", "T1"],
            "time_s": [0.0, 0.0],
            "gaze_x": [0.1, 0.2],
            "gaze_y": [0.2, 0.3],
            "pupil": [3.0, 3.1],
        }
    )
    with pytest.raises(ValueError, match="Subject-trial-time"):
        gp.prepare_gazepoint_gazer_input(duplicate)
    with pytest.raises(ValueError, match="Participant-trial-time"):
        gp.prepare_gazepoint_pupillometryr_input(duplicate)

    with pytest.raises(ValueError, match="participant/trial"):
        gp.prepare_gazepoint_gazer_input(pd.DataFrame({"trial": ["T"]}))
    with pytest.raises(ValueError, match="participant/trial"):
        gp.prepare_gazepoint_pupillometryr_input(pd.DataFrame({"trial": ["T"]}))


def test_data_quality_and_dashboard_alternative_paths(tmp_path):
    frame = pd.DataFrame({"x": [1.0, np.nan, 100.0], "label": ["a", "b", "c"]})

    no_files = gp.report_gazepoint_data_quality(
        {"frame": frame, "metadata": "skip"}, output_dir=tmp_path / "none", formats=()
    )
    assert no_files["paths"] == {}
    assert set(no_files["missingness"].column) == {"x", "label"}

    pdf = gp.report_gazepoint_data_quality(
        frame, output_dir=tmp_path / "pdf", formats=("pdf",), max_plot_columns=1
    )
    assert set(pdf["paths"]) == {"pdf"}

    with pytest.raises(ValueError, match="at least one row"):
        gp.pipeline_comparison_dashboard(pd.DataFrame())
    with pytest.raises(ValueError, match="Grouping columns not found"):
        gp.pipeline_comparison_dashboard(frame, grouping_cols="missing")

    ungrouped = gp.pipeline_comparison_dashboard(
        pd.DataFrame({"qc_status": ["pass", "review"], "excluded": [False, True]})
    )
    assert ungrouped["settings"]["grouping_cols"] == [".all"]
    assert ungrouped["overall"].loc[0, "n_issue_groups"] == 1

    grouped = gp.pipeline_comparison_dashboard(
        pd.DataFrame(
            {
                "participant": ["P1", "P1", "P2"],
                "missing_rate": [0.0, 0.2, 0.1],
                "quality": [1.0, 0.8, 0.9],
            }
        ),
        grouping_cols="participant",
    )
    assert grouped["overall"].loc[0, "n_groups"] == 2


def test_svm_feature_insufficient_and_point_process_alternatives():
    with pytest.raises(ValueError, match="eda_col"):
        gp.prepare_gazepoint_artifact_svm_features(pd.DataFrame({"x": [1.0]}))

    sparse = gp.prepare_gazepoint_artifact_svm_features(
        pd.DataFrame({"GSR_US": [1.0, np.nan]}), samples_per_segment=1
    )
    assert set(sparse.status) == {"insufficient_segment_data"}

    eda = pd.DataFrame(
        {
            "time": [0.0, 1.0, 2.0, 3.0],
            "GSR_US": [1.0, 1.1, 1.2, 1.3],
            "event_time": [0.0, np.nan, 2.0, np.nan],
        }
    )
    pp = gp.model_gazepoint_eda_point_process(
        eda, eda_col="GSR_US", time_col="time", event_time_col="event_time"
    )
    assert pp["process_summary"].loc[0, "n_events"] == 2

    hr = gp.model_gazepoint_hr_point_process(
        pd.DataFrame({"IBI": [0.8, 1.0, 0.9]}), ibi_units="auto"
    )
    assert hr["beat_table"].ibi_seconds.tolist() == [0.8, 1.0, 0.9]


def test_privacy_non_mapping_and_smoke_root_mode(tmp_path):
    privacy = gp.audit_gazepoint_smoke_privacy(pd.DataFrame({"aggregate": [1.0]}))
    assert privacy.loc[privacy.check == "aggregate_only", "status"].iloc[0] == "warn"

    root = tmp_path / "smoke"
    root.mkdir()
    (root / "sample.csv").write_text("x\n1\n", encoding="utf-8")
    smoke = gp.run_gazepoint_real_data_smoke(
        root,
        dataset_mode="root",
        workflow_runner=lambda **kwargs: {"ok": True},
        summary_runner=lambda workflow: {"summary": True},
        diagnostic_runner=lambda workflow, **kwargs: {"diagnostic": True},
    )
    assert smoke["results"].loc[0, "smoke_status"] == "pass"
    assert smoke["results"].loc[0, "n_files"] == 1
