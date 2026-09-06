import numpy as np
import pandas as pd

import gpbiometricspy as gp


def test_signal_quality_all_missing_reaches_empty_mad_path():
    quality = gp.compute_gazepoint_signal_quality(
        pd.DataFrame({"GSR": [np.nan, np.nan, np.nan]}),
        signal_cols="GSR",
    )

    assert quality.loc[0, "n_finite"] == 0
    assert np.isnan(quality.loc[0, "mad"])
