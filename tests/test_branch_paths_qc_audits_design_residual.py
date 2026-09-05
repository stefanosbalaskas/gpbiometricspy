import pandas as pd

import gpbiometricspy as gp


def test_correct_beats_uses_group_median_when_local_window_has_no_clean_reference():
    out = gp.correct_gazepoint_beats(
        pd.DataFrame({"ibi": [100.0, 120.0, 800.0]}),
        action="local_median",
        local_window=1,
        ibi_col="ibi",
        min_ibi=300,
        max_ibi=2000,
    )

    log = out["correction_log"]
    group_rows = log[log["correction_note"] == "replaced_with_group_median"]
    assert len(group_rows) == 1
    assert group_rows["corrected_ibi"].iloc[0] == 800.0
