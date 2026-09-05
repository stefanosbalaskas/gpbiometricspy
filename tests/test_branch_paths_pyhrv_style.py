from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_pyhrv_frequency_short_resampling_and_ar_guardrails():
    short_welch = gp.compute_gazepoint_pyhrv_welch_psd([800.0, 810.0, 820.0])
    assert short_welch["psd"].empty

    constant_time = gp.compute_gazepoint_pyhrv_welch_psd(
        [800.0, 810.0, 820.0, 830.0],
        time_s=[1.0, 1.0, 1.0, 1.0],
    )
    assert constant_time["psd"].empty

    small_grid = gp.compute_gazepoint_pyhrv_welch_psd(
        [800.0, 810.0, 820.0, 830.0], resample_hz=1
    )
    assert small_grid["psd"].empty

    short_ar = gp.compute_gazepoint_pyhrv_ar_psd(
        [800.0, 810.0, 820.0, 830.0], resample_hz=2
    )
    assert short_ar["psd"].empty

    invalid_order = gp.compute_gazepoint_pyhrv_ar_psd(
        800.0 + 5.0 * np.sin(np.linspace(0, 4 * np.pi, 40)), order=0
    )
    assert invalid_order["psd"].empty

    short_lomb = gp.compute_gazepoint_pyhrv_lomb_psd([800.0, 810.0, 820.0])
    assert short_lomb["psd"].empty


def test_pyhrv_interval_extraction_and_segmentation_guardrails():
    with pytest.raises(ValueError, match="time_unit"):
        gp.extract_gazepoint_pyhrv_nn_intervals([0.0, 1.0], time_unit="minutes")

    with pytest.raises(ValueError, match="peak_time_col"):
        gp.extract_gazepoint_pyhrv_nn_intervals(pd.DataFrame({"time": [0.0, 1.0]}))

    one_peak = gp.extract_gazepoint_pyhrv_nn_intervals([1.0])
    assert one_peak.size == 0

    milliseconds = gp.extract_gazepoint_pyhrv_nn_intervals(
        pd.DataFrame({"peak_time_s": [1000.0, 1800.0, 2600.0]}),
        time_unit="milliseconds",
    )
    assert milliseconds.tolist() == [800.0, 800.0]

    assert gp.segment_gazepoint_pyhrv_nni([]).empty
    assert gp.segment_gazepoint_pyhrv_nni(
        [800.0] * 8, segment_seconds=60, min_intervals=100
    ).empty

    assert np.isnan(gp.compute_gazepoint_pyhrv_sdnn_index([800.0, 810.0]))
    assert np.isnan(gp.compute_gazepoint_pyhrv_sdann([800.0, 810.0]))
    assert np.isnan(gp.compute_gazepoint_pyhrv_triangular_index([800.0, 810.0]))
    assert np.isnan(gp.compute_gazepoint_pyhrv_tinn([800.0, 810.0]))


def test_pyhrv_waterfall_and_nonlinear_edge_paths():
    waterfall = gp.compute_gazepoint_pyhrv_psd_waterfall(
        [800.0, 810.0], segment_seconds=60
    )
    assert waterfall["psd"].empty
    assert waterfall["measures"].empty

    poincare = gp.compute_gazepoint_pyhrv_poincare([800.0, 810.0])
    assert poincare[["sd1", "sd2"]].isna().all(axis=None)

    assert np.isnan(gp.compute_gazepoint_pyhrv_sample_entropy([800.0, 810.0, 820.0]))
    assert np.isnan(gp.compute_gazepoint_pyhrv_sample_entropy([800.0] * 10))

    dfa = gp.compute_gazepoint_pyhrv_dfa(
        800.0 + np.arange(20.0), scales=[2, 100]
    )
    assert dfa[["alpha", "alpha1", "alpha2"]].isna().all(axis=None)

    with pytest.raises(ValueError, match="No valid NN intervals"):
        gp.plot_gazepoint_pyhrv_tachogram([np.nan, 100.0])

    with pytest.raises(ValueError, match="At least three"):
        gp.plot_gazepoint_pyhrv_hr_heatplot([800.0, 810.0])

    with pytest.raises(ValueError, match="No finite radar values"):
        gp.plot_gazepoint_pyhrv_radar_chart({"sdnn": np.nan})


def test_pyhrv_json_scalar_list_and_export_path_guardrails(tmp_path):
    with pytest.raises(ValueError, match="Supply `path`"):
        gp.export_gazepoint_pyhrv_results({}, "")

    path = tmp_path / "edge.json"
    gp.export_gazepoint_pyhrv_results(
        {
            "scalar": np.float64(1.5),
            "integer": np.int64(2),
            "items": [np.float64(3.5), (np.int64(4),)],
        },
        path,
    )
    loaded = gp.import_gazepoint_pyhrv_results(path)
    assert loaded["scalar"] == 1.5
    assert loaded["integer"] == 2
    assert loaded["items"] == [3.5, [4]]


def test_prepare_pyhrv_input_additional_validation_paths():
    base = [800.0, 810.0]

    with pytest.raises(ValueError, match="invalid unit"):
        gp.prepare_gazepoint_pyhrv_input(base, unit="ticks")
    with pytest.raises(ValueError, match="invalid filter"):
        gp.prepare_gazepoint_pyhrv_input(base, unit="milliseconds", filter="bad")
    with pytest.raises(ValueError, match="bounds must be positive"):
        gp.prepare_gazepoint_pyhrv_input(
            base, unit="milliseconds", min_nni_ms=0
        )
    with pytest.raises(ValueError, match="prefix"):
        gp.prepare_gazepoint_pyhrv_input(
            base, unit="milliseconds", prefix=""
        )
    with pytest.raises(ValueError, match="at least one row"):
        gp.prepare_gazepoint_pyhrv_input(pd.DataFrame())

    numeric = pd.DataFrame({"rr_custom": [800.0, 810.0]})
    with pytest.raises(ValueError, match="ibi_col.*not found"):
        gp.prepare_gazepoint_pyhrv_input(
            numeric, ibi_col="missing", unit="milliseconds"
        )

    with pytest.raises(ValueError, match="numeric column"):
        gp.prepare_gazepoint_pyhrv_input(
            pd.DataFrame({"rr_custom": ["800", "810"]}),
            ibi_col="rr_custom",
            unit="milliseconds",
        )

    explicit = gp.prepare_gazepoint_pyhrv_input(
        numeric, ibi_col="rr_custom", unit="milliseconds"
    )
    assert explicit["settings"]["ibi_col"] == "rr_custom"
    assert explicit["settings"]["unit_resolution_method"] == "explicit"


def test_prepare_pyhrv_auto_unit_and_multigroup_paths():
    column_seconds = gp.prepare_gazepoint_pyhrv_input(
        pd.DataFrame({"RR_seconds": [0.8, 0.81]}),
        ibi_col="RR_seconds",
        unit="auto",
    )
    assert column_seconds["settings"]["resolved_unit"] == "seconds"
    assert column_seconds["settings"]["unit_resolution_method"] == "column_name"

    auto_ms = gp.prepare_gazepoint_pyhrv_input([800.0, 810.0], unit="auto")
    assert auto_ms["settings"]["resolved_unit"] == "milliseconds"
    assert auto_ms["settings"]["unit_resolution_method"] == "median_heuristic"

    with pytest.raises(ValueError, match="finite positive"):
        gp.prepare_gazepoint_pyhrv_input([np.nan, -1.0], unit="auto")

    grouped = gp.prepare_gazepoint_pyhrv_input(
        pd.DataFrame(
            {
                "participant": ["P1", "P1", "P2"],
                "session": [1.0, np.nan, 1.0],
                "RR_ms": [800.0, 810.0, 900.0],
            }
        ),
        group_cols=["participant", "session"],
    )
    assert len(grouped["vectors"]) == 3
    assert any("<NA>" in key for key in grouped["vectors"])
