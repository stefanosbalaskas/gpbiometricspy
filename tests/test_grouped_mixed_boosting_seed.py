from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gpbiometricspy import grouped_mixed_boosting as gm


def _frame(groups=6, rows=6):
    rng = np.random.default_rng(13)
    records = []
    for group in range(groups):
        for _ in range(rows):
            x = rng.normal()
            records.append({"group": f"g{group}", "x": x, "y": x + 0.2 * group + rng.normal(0, 0.05)})
    return pd.DataFrame(records)


def test_seed_changes_balanced_tie_assignment():
    groups = np.array([f"g{i}" for i in range(8) for _ in range(3)], dtype=object)
    fold_1 = gm._group_folds(groups, 4, 1)
    fold_2 = gm._group_folds(groups, 4, 2)
    assert [tuple(fold) for fold in fold_1] != [tuple(fold) for fold in fold_2]


def test_seed_is_fail_closed_for_cv_and_permutation():
    data = _frame()
    model = gm.fit_grouped_mixed_boosting(
        data,
        outcome_col="y",
        group_col="group",
        feature_cols=["x"],
        n_estimators=3,
        min_samples_leaf=2,
        max_iterations=2,
    )
    with pytest.raises(ValueError, match="non-negative integer"):
        gm.group_aware_permutation_importance(model, data, repeats=1, seed=-1)
    with pytest.raises(ValueError, match="non-negative integer"):
        gm.group_aware_permutation_importance(model, data, repeats=1, seed=True)
    with pytest.raises(ValueError, match="non-negative integer"):
        gm.grouped_cross_validation_mixed_boosting(
            data,
            outcome_col="y",
            group_col="group",
            feature_cols=["x"],
            n_splits=3,
            seed=1.5,
        )
