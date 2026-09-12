# Hierarchical location–scale modelling

`gpbiometricspy.hierarchical_location_scale` provides a Python-native Gaussian hierarchical location–scale model for repeated biometric or eye-tracking outcomes. This is an additive methods extension and is intentionally separate from the frozen 406-function `gpbiometrics` R semantic-parity contract.

## Model

For observation *i* from participant/group *j*, the conditional outcome model is

\[
y_{ij} \sim \mathcal{N}(\mu_{ij},\sigma_{ij}^2),
\]

with

\[
\mu_{ij}=x_{ij}^{\mathsf T}\beta+u_j,
\qquad
\log \sigma_{ij}=z_{ij}^{\mathsf T}\gamma+v_j,
\]

and correlated group-level random intercepts

\[
(u_j,v_j)^{\mathsf T}\sim\mathcal{N}(0,\Sigma).
\]

The fitted random-effect parameters are the location SD, log-scale SD, and their correlation. Marginal likelihood contributions are evaluated with two-dimensional adaptive Gauss–Hermite quadrature; fixed effects and covariance parameters are optimized jointly.

## Minimal example

```python
from gpbiometricspy.hierarchical_location_scale import (
    fit_gazepoint_hierarchical_location_scale,
    predict_gazepoint_hierarchical_location_scale,
    simulate_gazepoint_hierarchical_location_scale,
)

data = simulate_gazepoint_hierarchical_location_scale(seed=42)

fit = fit_gazepoint_hierarchical_location_scale(
    data,
    outcome_col="outcome",
    group_col="participant",
    mean_cols=["x"],
    scale_cols=["x"],
    quadrature_points=7,
)

pred = predict_gazepoint_hierarchical_location_scale(fit, data.head())
```

Numeric predictors can be standardized automatically. Categorical predictors use deterministic treatment coding with the lexicographically first observed level as reference. The mean and scale equations may use different predictor sets. Predictor lists are not allowed to reuse the outcome or grouping column, preventing accidental outcome leakage or duplication of the participant identifier as a fixed-effect predictor.

## Prediction semantics

For a participant/group seen during fitting, conditional prediction uses the empirical-Bayes location and log-scale random-effect summaries. For an unseen participant/group, the function returns an explicit population-level prediction and labels the source `population_unseen_group`. Setting `include_random_effects=False` always requests population-level prediction.

This distinction is deliberate: an unobserved participant does not have an estimated participant-specific random effect.

## Reproducibility certificate

`create_gazepoint_hierarchical_location_scale_certificate()` creates a compact SHA-256 certificate over the model version, canonical input-data fingerprint, model terms, fitted parameters, quadrature resolution, and an explicit converged-fit state. Validation canonicalizes JSON key order, so semantically identical payloads do not fail merely because dictionary key order changed. Parameter tampering invalidates the certificate.

Certificate creation is fail-closed: a fit retained with `require_convergence=False` for diagnostic inspection cannot be certified unless the optimizer nevertheless reports convergence. This prevents a non-converged exploratory result from being promoted to a reproducibility-certified result.

## Scientific boundaries

The model estimates distributional heterogeneity conditional on its stated Gaussian specification. It does **not** establish that changing residual scale is caused by motion, artifacts, sensor quality, emotion, arousal, attention, cognition, health status, or any other latent process. It does not perform artifact correction or sensor-validity weighting. Random effects are empirical-Bayes summaries conditional on the fitted model, not directly observed participant traits.

Current scope is intentionally conservative: Gaussian outcomes, random intercepts in the location and log-scale equations, complete-case fitting, and a single correlated two-dimensional group-level random-effect block. Random slopes, crossed random effects, non-Gaussian likelihoods, Bayesian priors, and causal interpretation are outside this tranche.

## Validation strategy

The package test contract covers deterministic known-truth simulation, parameter-direction recovery, convergence diagnostics, empirical-Bayes versus unseen-group prediction behavior, categorical-level guardrails, reserved-column leakage guardrails, structural immutability of fitted metadata, and certificate tamper/non-convergence rejection. These tests establish software and method-contract behavior; they are not a substitute for empirical validation on a particular sensor, population, or scientific construct.