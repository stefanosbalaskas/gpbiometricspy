import numpy as np
import pandas as pd

import gpbiometricspy as gp


def test_explicit_remaining_pyhrv_metric_surface():
    # Long enough to exercise segmented metrics and the waterfall path.
    nni = 800 + 35 * np.sin(np.linspace(0, 12 * np.pi, 900))

    assert len(gp.compute_gazepoint_pyhrv_nn_diff(nni)) == len(nni) - 1
    assert len(gp.compute_gazepoint_pyhrv_nni_parameters(nni)) == 1
    assert len(gp.compute_gazepoint_pyhrv_nni_differences_parameters(nni)) == 1
    assert len(gp.compute_gazepoint_pyhrv_hr_parameters(nni)) == 1

    assert np.isfinite(gp.compute_gazepoint_pyhrv_sdnn(nni))
    assert np.isfinite(gp.compute_gazepoint_pyhrv_rmssd(nni))
    assert np.isfinite(gp.compute_gazepoint_pyhrv_sdsd(nni))
    assert np.isfinite(gp.compute_gazepoint_pyhrv_sdann(nni, segment_seconds=60))
    assert np.isfinite(gp.compute_gazepoint_pyhrv_sdnn_index(nni, segment_seconds=60))
    assert np.isfinite(gp.compute_gazepoint_pyhrv_triangular_index(nni))
    assert np.isfinite(gp.compute_gazepoint_pyhrv_tinn(nni))

    freq = gp.compute_gazepoint_pyhrv_frequency_domain(nni, method="welch")
    assert "measures" in freq and "psd" in freq
    waterfall = gp.compute_gazepoint_pyhrv_psd_waterfall(nni, segment_seconds=60, method="welch")
    assert "psd" in waterfall and "measures" in waterfall


def test_explicit_american_zscore_alias():
    dat = pd.DataFrame(
        {
            "participant": ["P01"] * 4 + ["P02"] * 4,
            "SCR_Amplitude": [1.0, 2.0, 3.0, 4.0, 4.0, 6.0, 8.0, 10.0],
        }
    )
    out = gp.standardize_gazepoint_zscore(
        dat, signal_col="SCR_Amplitude", group_col="participant"
    )
    assert "SCR_Amplitude_Z" in out.columns
    assert np.allclose(
        out.groupby("participant")["SCR_Amplitude_Z"].mean().to_numpy(), 0.0
    )
