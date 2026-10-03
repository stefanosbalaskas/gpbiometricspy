from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_generator_exercises_retention_without_baking_ita_into_hr_error(tmp_path):
    module = _load_script("generate_ppg_equity_synthetic_demo.py")
    data = module.generate_synthetic_ppg_equity(
        seed=17,
        n_participants=8,
        sampling_rate_hz=60,
        seconds_per_activity=2,
    )
    required = {
        "participant",
        "activity",
        "HRP",
        "ecg_hr",
        "ppg_hr",
        "ita_degrees",
        "skin_L_star",
        "skin_b_star",
    }
    assert required <= set(data.columns)
    assert data["participant"].nunique() == 8
    assert set(data["activity"]) == {"Rest", "Typing", "Walk"}
    summary = module._participant_activity_summary(data)
    assert summary["hr_retention"].between(0, 1).all()
    artifacts = module.render_figures(data, tmp_path)
    keys = [
        "retention_figure",
        "reference_error_figure",
        "waveform_figure",
        "bin_summary",
        "participant_summary",
    ]
    for key in keys:
        assert (tmp_path / artifacts[key]).exists()


def test_step_adapter_validates_official_schema_and_runs_reference_audit(tmp_path):
    module = _load_script("run_step_ppg_equity_evidence.py")
    rows = []
    rng = np.random.default_rng(7)
    for participant in range(1, 7):
        for activity in ["Rest", "Activity", "Breathe", "Type"]:
            for _ in range(4):
                ecg = 65 + 5 * (activity == "Activity") + rng.normal(0, 1)
                row = {
                    "ECG": ecg,
                    "ID": participant,
                    "Skin Tone": participant,
                    "Activity": activity,
                }
                for device in module.STEP_DEVICE_COLUMNS:
                    row[device] = ecg + rng.normal(0, 2 + 2 * (activity == "Activity"))
                rows.append(row)
    data = pd.DataFrame(rows)
    report = module.schema_report(data)
    assert report["participants"] == 6
    assert report["schema_status"] == "qualified"
    long = module.reshape_step(data)
    assert set(long["device"]) == set(module.STEP_DEVICE_COLUMNS)

    from gpbiometricspy.ppg_equity import compare_ppg_reference_by_pigmentation

    result = compare_ppg_reference_by_pigmentation(
        long,
        participant_col="participant",
        reference_col="ecg_hr",
        candidate_col="wearable_hr",
        pigmentation_col="fitzpatrick",
        pigmentation_metric="fitzpatrick",
        metric_name="heart_rate",
        device_col="device",
        condition_col="activity",
        n_boot=5,
        random_state=7,
    )
    module.write_derived_outputs(result, tmp_path)
    assert (tmp_path / "step-agreement-by-device-activity.csv").exists()
    warning = "continuous_association_models_not_run_for_nonobjective_pigmentation_metric"
    assert warning in result["warnings"]


def test_encode_adapter_inventories_objective_subjective_and_site_metadata():
    module = _load_script("run_encode_pigmentation_schema_stress.py")
    concept = pd.DataFrame(
        {
            "concept_id": [2001, 2002, 2003, 3001],
            "concept_name": [
                "Skin color L* finger left dorsal colorimetry",
                "Skin color b* finger left dorsal colorimetry",
                "Monk Skin Tone finger left dorsal",
                "Serum sodium",
            ],
        }
    )
    measurement = pd.DataFrame(
        {
            "person_id": [1, 1, 1, 2, 2, 2],
            "measurement_concept_id": [2001, 2002, 2003, 2001, 2002, 2003],
            "value_as_number": [60.0, 18.0, 4.0, 42.0, 17.0, 8.0],
        }
    )
    inventory, report = module.inventory_encode(measurement, concept)
    assert report["schema_status"] == "qualified"
    assert report["skin_measurement_rows"] == 6
    assert report["objective_or_instrumental_concepts"] == 2
    assert report["subjective_scale_concepts"] == 1
    assert inventory["mentions_anatomical_site"].all()
