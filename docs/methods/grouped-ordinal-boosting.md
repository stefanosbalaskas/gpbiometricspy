# Grouped ordinal mixed-effects boosting

## Status

**Certified development method.** The method was introduced through PR **#130** and exact-main certified at merge SHA `36d413f5dfa5f42acb1c6c80295b6904162402e8`, tree `8256d5bc047b3da3ebe6e244d6bbaa5edb60f0f5`. It is additive to the frozen **406/406** `gpbiometrics 2.0.0` parity surface and is not part of stable release `gpbiometricspy 0.1.6`.

## Why this method exists

Repeated-measures eye-tracking and psychophysiology studies often contain **ordered outcomes** rather than continuous responses: confidence ratings, discomfort levels, perceived workload, trust categories, ordered safety judgements, or ordinal behavioural codes. Treating those outcomes as Gaussian can ignore their threshold structure, while ordinary ordinal classifiers can ignore participant/group clustering.

Recent methodological work has made the gap especially visible. Bergonzoli, Rossi and Masci (2026) introduced **Ordinal Mixed-Effects Random Forests (OMERF)**, alternating a random-forest fixed component with a cumulative-link mixed-effects component. Buczak (2025) proposed the **Mixed-Effects Frequency-Adjusted Borders Ordinal Forest** for clustered ordinal prediction. These contributions establish the relevance of flexible nonlinear ordinal mixed-effects prediction, but they do not provide a dependency-light Python workflow aligned with `gpbiometricspy`'s deterministic provenance, group-held-out validation, and explicit seen-versus-unseen group semantics.

The implementation here is therefore an independent **deterministic shallow-tree boosting analogue for one grouping factor**. It is **not** an implementation, reproduction, or Python port of OMERF, mixfabOF, XGBoost, or any random-forest algorithm.

## Model

For ordered outcome categories `1, ..., K`, the model uses a proportional-odds cumulative-logit representation:

\[
P(Y_i \le k \mid x_i, b_{g[i]}) = \operatorname{logit}^{-1}(\theta_k - f(x_i) - b_{g[i]}),
\]

where:

- `theta_k` are strictly ordered cut-points;
- `f(x_i)` is a deterministic shallow-tree boosting predictor;
- `b_g` is a shrinkage-estimated group random intercept;
- one grouping factor is supported.

The fitting algorithm alternates among three components:

1. **ordinal score boosting** for the nonlinear fixed component;
2. **group offset estimation and empirical-Bayes-style shrinkage** for the group intercepts; and
3. **ordered threshold optimization** under a monotonic gap parameterization.

This is a pragmatic predictive approximation. It does not evaluate a fully integrated cumulative-link mixed-model likelihood over the random-effects distribution and must not be described as a conventional CLMM estimator.

## Category ordering is fail-closed

Ordinal ordering is scientifically substantive. The implementation therefore does not silently sort strings or numeric labels.

The caller must either:

- supply `category_order=[...]` explicitly; or
- provide the outcome as an **ordered pandas categorical**.

At least three ordered categories are required, every declared category must be observed in the training data, and category labels must be unique finite scalar strings or numbers. Ambiguous ordering fails before model fitting.

## Prediction semantics

The method deliberately distinguishes two prediction targets.

### Marginal prediction

`mode="marginal"` omits fitted group offsets. This is the appropriate default for a genuinely new group whose latent intercept was not observed during training.

### Conditional prediction

`mode="conditional"` adds the fitted shrinkage-estimated intercept for groups observed during training. For an unseen group, the default is explicit fallback to the marginal prediction; `unseen_group="error"` instead fails closed.

Predictions can be returned as:

- category probabilities;
- cumulative probabilities; or
- the highest-probability category label.

## Whole-group cross-validation

Random row-wise cross-validation leaks information whenever rows from the same participant/group appear in both train and test data. `grouped_cross_validation_ordinal_boosting()` therefore partitions **whole groups**.

For each held-out fold it reports out-of-fold predictions and ordinal performance including:

- negative log loss;
- ranked probability score (RPS); and
- mean absolute error on ordered category indices.

The evaluation target is explicitly **new-group generalization** because held-out groups are not supplied fitted training-group offsets.

## Group-aware permutation importance

`group_aware_ordinal_permutation_importance()` uses the increase in ranked probability score as its default predictive-importance quantity.

Permutation respects predictor level:

- predictors that vary within groups are shuffled **within each group**;
- predictors that are constant within groups are permuted **at the group level**.

This prevents a group-level variable from being transformed into an impossible within-participant pattern during importance analysis.

Permutation importance is predictive. It is not a causal estimand and does not establish mediation, mechanism, or variable necessity.

## Reproducibility certificate

`create_grouped_ordinal_boosting_certificate()` binds the fitted model's schema, category order, thresholds, tree structure, group effects, training digests, hyperparameters, convergence state, and training scores into a deterministic canonical SHA-256 payload. `validate_grouped_ordinal_boosting_certificate()` recomputes that payload and fails on tampering.

The certificate establishes reproducible object identity. It does not establish external validity, sensor validity, model adequacy, or truth of scientific interpretation.

## Certified validation evidence

PR **#130** was qualified on immutable candidate head `89ea07a3cf38b59d3486f58453b327b2952174b4`; the certified merge tree exactly matches candidate tree `8256d5bc047b3da3ebe6e244d6bbaa5edb60f0f5`.

At certification, exact-main software evidence passed **799/799 tests** and **14,402/14,402 statements**. Repository-wide raw branch coverage was **6,895/6,914 = 99.7252%**, with exactly **19** audited structural/caller-dominated residual arcs and **0 unexpected, 0 stale, 0 unaudited** branch debt. The grouped ordinal implementation itself passed **387/387 statements** and **138/138 branches**.

Those figures identify the historical certification point for this method. Later development-line certification adds other methods and therefore has larger repository-wide denominators; it does not retroactively change the PR #130 evidence.

The synthetic known-truth validation injects monotonic group heterogeneity, requires strong recovery of the group ordering, and requires fitted conditional RPS to improve over a class-frequency null.

## Scientific guardrails

The method is intended for nonlinear **prediction of ordered outcomes with one grouping factor**. It does not by itself:

- provide likelihood-based p-values or confidence intervals;
- estimate a fully integrated cumulative-link mixed model;
- implement OMERF, mixfabOF, random forests, or XGBoost;
- support crossed random effects or random slopes;
- justify treating fitted group effects as stable participant traits;
- identify causal effects or mechanisms;
- diagnose emotion, stress, trust, impairment, disease, or other latent states;
- detect eye-tracking or physiological artifacts; or
- establish sensor validity or measurement reliability.

## References

Bergonzoli, G., Rossi, G., & Masci, C. (2026). Ordinal Mixed-Effects Random Forests. *Journal of Classification*. https://doi.org/10.1007/s00357-026-09558-1

Buczak, P. (2025). Mixed-Effects Frequency-Adjusted Borders Ordinal Forest. *Multivariate Behavioral Research*. https://doi.org/10.1080/00273171.2025.2547416
