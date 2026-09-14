# Grouped mixed-effects boosting

`gpbiometricspy.grouped_mixed_boosting` is a Python-native nonlinear prediction method for **continuous outcomes observed repeatedly within one grouping factor**. It combines a deterministic shallow regression-tree booster for nonlinear fixed structure with empirical-Bayes random intercepts for group dependence.

The method is intended for predictive and exploratory modelling of clustered behavioral and psychophysiological data. It is **not** a causal model, not an XGBoost implementation, and not a replacement for likelihood-based mixed models when formal mixed-model inference is the primary objective.

## Motivation

Recent mixed-effects machine-learning work emphasizes that a flexible nonlinear learner alone does not resolve dependence in multilevel data. It also shows that evaluation and variable-importance procedures must respect the grouping structure rather than randomly split or permute individual rows.

The 2026 Psychometrika LMM–XGBoost framework combines XGBoost with mixed effects, distinguishes conditional predictions for observed clusters from marginal predictions for unseen clusters, proposes group-aware permutation importance, and uses group-aware cross-validation. See Cho and Mueller (2026), DOI [10.1017/psy.2026.10108](https://doi.org/10.1017/psy.2026.10108).

`gpbiometricspy` adopts those **design principles**, but implements a narrower dependency-free model so the package does not require XGBoost or scikit-learn.

## Model scope

For observation \(i\) in group \(g\), the working model is

```text
y_i = f(x_i) + b_g + e_i
```

where:

- `f(x)` is a deterministic gradient-boosted ensemble of shallow regression trees;
- `b_g` is a Gaussian-style random intercept estimated with empirical-Bayes shrinkage; and
- `e_i` is the residual component.

Version 1 supports:

- one grouping factor;
- continuous outcomes;
- numeric finite predictors;
- shallow trees of depth 1–3;
- marginal and conditional prediction;
- whole-group cross-validation;
- level-aware permutation importance; and
- deterministic model certificates.

It does not currently support crossed random effects, random slopes, binary/count outcomes, missing-value routing, categorical split optimization, or likelihood-based uncertainty intervals.

## Fit a model

```python
from gpbiometricspy.grouped_mixed_boosting import fit_grouped_mixed_boosting

model = fit_grouped_mixed_boosting(
    data,
    outcome_col="pupil_change",
    group_col="participant",
    feature_cols=["trial_time", "difficulty", "gaze_entropy"],
    n_estimators=50,
    learning_rate=0.05,
    max_depth=2,
    min_samples_leaf=5,
    max_iterations=20,
    tolerance=1e-5,
)
```

At least four distinct groups are required. Outcome, grouping, and feature roles must be distinct. Predictors and outcomes must be finite numeric values; missingness should be handled explicitly upstream rather than being silently routed through tree splits.

### Alternating estimator

Each outer iteration performs four steps:

1. subtract the current random-intercept contribution from the outcome;
2. fit the shallow-tree booster to the adjusted outcome;
3. estimate one-way random-intercept and residual variance components from `y - f(x)` using a method-of-moments decomposition; and
4. compute shrinkage-weighted empirical-Bayes group intercepts.

Iteration stops when the maximum absolute change in group effects is no larger than `tolerance`, or when `max_iterations` is reached.

The returned model records `converged` and `n_iterations`. Non-convergence is reported rather than silently converted into success.

## Shallow nonlinear fixed component

The fixed component uses deterministic squared-error regression trees. At each node, candidate numeric thresholds are evaluated exhaustively and the split with the largest reduction in sum of squared errors is selected. Boosting then fits successive trees to residuals:

```text
f_0(x) = mean(y*)
f_m(x) = f_(m-1)(x) + learning_rate × tree_m(x)
```

where `y*` is the outcome after subtracting the current random-intercept contribution.

`max_depth` is deliberately capped at 3. This keeps the learner interpretable enough for methodological inspection and avoids presenting a compact research implementation as a general-purpose industrial boosting library.

## Marginal versus conditional prediction

```python
from gpbiometricspy.grouped_mixed_boosting import predict_grouped_mixed_boosting

marginal = predict_grouped_mixed_boosting(
    model,
    new_data,
    mode="marginal",
)

conditional = predict_grouped_mixed_boosting(
    model,
    new_data,
    mode="conditional",
)
```

### Marginal prediction

`mode="marginal"` returns only the nonlinear fixed component:

```text
f(x)
```

This is the appropriate default for genuinely new groups because no empirical-Bayes random intercept is available for them.

### Conditional prediction

`mode="conditional"` adds the fitted random intercept when the group was observed during training:

```text
f(x) + b_g
```

For an unseen group, the default `unseen_group="marginal"` uses a zero random effect and therefore falls back to the marginal prediction. Set `unseen_group="error"` to fail instead.

This distinction is substantive. Good within-participant conditional prediction does not by itself demonstrate generalization to new participants.

## Whole-group cross-validation

```python
from gpbiometricspy.grouped_mixed_boosting import grouped_cross_validation_mixed_boosting

cv = grouped_cross_validation_mixed_boosting(
    data,
    outcome_col="pupil_change",
    group_col="participant",
    feature_cols=["trial_time", "difficulty", "gaze_entropy"],
    n_splits=5,
    seed=2026,
    n_estimators=50,
    learning_rate=0.05,
    max_depth=2,
    min_samples_leaf=5,
)

print(cv["rmse"])
print(cv["folds"])
```

Groups are indivisible fold units: no group can contribute rows to both training and test data within a fold. Test-fold predictions are always **marginal unseen-group predictions**.

The fold allocator balances row counts approximately while preserving entire groups. Every training fold must retain at least four distinct groups.

This evaluation answers a more defensible question than row-wise random CV:

> How well does the nonlinear fixed component generalize to groups that were absent from model estimation?

It does not estimate conditional performance for future observations from already-calibrated groups.

## Group-aware permutation importance

```python
from gpbiometricspy.grouped_mixed_boosting import group_aware_permutation_importance

importance = group_aware_permutation_importance(
    model,
    data,
    repeats=100,
    seed=2026,
    prediction_mode="marginal",
)
```

The function first classifies each feature by its observed grouping level.

### Within-group predictors

If a predictor varies within at least one group, values are shuffled **within groups**. This destroys the predictor–outcome relationship without manufacturing values across group boundaries.

### Group-level predictors

If a predictor is constant within every group, group-level values are permuted **between whole groups** and then copied back to all rows in each group. This avoids a meaningless row-wise shuffle of a cluster-constant variable.

Importance is reported as the increase in mean squared error relative to the unpermuted baseline, together with the repeat-to-repeat SD.

For scientific reporting, permutation importance should be interpreted as predictive contribution under the stated model, prediction mode, and permutation design. It is not a causal effect and does not establish construct validity.

## Random-intercept variance and shrinkage

Given residuals after the fixed nonlinear component, the implementation estimates within-group residual variance and between-group random-intercept variance using a one-way method-of-moments decomposition that accounts for unequal group sizes through the effective group-size term.

Each group residual mean is then shrunk toward the overall residual mean. Smaller groups and noisier data receive more shrinkage; when estimated between-group variance is zero, fitted random intercepts reduce to zero.

These are empirical-Bayes-style predictions under a working Gaussian random-intercept interpretation. They are not posterior draws or Bayesian credible intervals.

## Reproducibility certificate

```python
from gpbiometricspy.grouped_mixed_boosting import (
    create_grouped_mixed_boosting_certificate,
    validate_grouped_mixed_boosting_certificate,
)

certificate = create_grouped_mixed_boosting_certificate(model)
assert validate_grouped_mixed_boosting_certificate(model, certificate)
```

The certificate binds:

- outcome/group/feature schema;
- complete shallow-tree structure and thresholds;
- learning rates;
- fitted group levels and empirical-Bayes effects;
- estimated variance components;
- convergence state;
- hyperparameters;
- training row/group counts; and
- SHA-256 hashes of the training outcome and feature matrix.

The certificate is deterministic and JSON-key-order independent. It is a reproducibility binding, not a digital signature or proof that the chosen model is scientifically appropriate.

## Recommended evaluation pattern

For clustered psychophysiological or behavioral prediction, report at least:

1. the grouping unit and number of groups;
2. the nonlinear learner hyperparameters;
3. convergence state and variance components;
4. conditional training/diagnostic performance only when clearly labelled as within-observed-group performance;
5. whole-group OOF marginal RMSE/MSE for new-group generalization; and
6. group-aware rather than globally shuffled permutation importance.

Do not use ordinary row-wise random splits as the primary evidence for participant-level generalization when repeated observations from the same participant occur on both sides of the split.

## Relationship to the location–scale family

The hierarchical location–scale methods elsewhere in `gpbiometricspy` are model-based tools for mean and residual-scale heterogeneity with explicit parametric equations and random effects. Grouped mixed boosting addresses a different problem: flexible nonlinear **prediction** of the conditional mean when repeated observations are clustered.

The two families should not be conflated. A strong nonlinear predictive association does not imply a causal mechanism, and the boosting model does not estimate a participant-specific residual-scale equation.

## Relationship to published mixed-effects ML

Cho and Mueller (2026) develop a substantially richer LMM–XGBoost method for cross-classified continuous outcomes, including XGBoost, multiple random-effect factors, combined-group CV, and group-aware permutation importance. The present implementation is an independent, narrower single-group analogue intended to make the core leakage-resistant workflow available without adding an external boosting dependency.

Accordingly, results from `grouped_mixed_boosting` should be described by its own method name and implementation details—not as results from LMM–XGBoost.

## Scientific boundaries

This method does not by itself:

- identify causal effects;
- establish physiological construct validity;
- prove that a feature measures stress, trust, workload, emotion, preference, or diagnosis;
- correct artifacts or validate sensors;
- justify population generalization without held-out-group evaluation;
- provide likelihood-ratio tests, p-values, or mixed-model confidence intervals; or
- support crossed/random-slope claims that are not part of the implemented model.

The primary contribution is methodological discipline around **nonlinear prediction with clustered data**: explicit random-intercept dependence, new-group prediction semantics, whole-group evaluation, and grouping-aware importance.
