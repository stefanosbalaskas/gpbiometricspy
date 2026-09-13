# Random scale-slope hierarchical location–scale modelling

This Python-native method extends the Gaussian hierarchical location–scale family with **one participant/group-specific numeric slope in the log-scale equation**. It is designed for repeated-measures settings where the association between a within-group covariate and conditional residual variability may itself differ across participants or groups.

The random-effects vector is

`(location intercept, log-scale intercept, log-scale slope)`

with a full positive-definite **3 × 3 covariance matrix**. Group marginal likelihoods are evaluated with **three-dimensional adaptive Gauss–Hermite quadrature**.

## Model

For observation `i` in group `g`, the model is

- `y_ig ~ Normal(mu_ig, sigma_ig)`
- `mu_ig = X_ig beta + u_g`
- `log(sigma_ig) = Z_ig gamma + v0_g + v1_g r_ig`

where `(u_g, v0_g, v1_g)` follows a zero-mean multivariate Gaussian distribution with an unrestricted positive-definite covariance matrix.

The random scale-slope predictor `r` must:

1. be numeric;
2. also appear in the fixed `scale_cols` equation; and
3. vary within every participant/group.

The implementation rejects unidentified random-slope specifications before numerical optimization and requires at least six groups for covariance estimation.

## Fit the model

```python
from gpbiometricspy.hierarchical_location_scale_random_scale_slope import (
    fit_gazepoint_hierarchical_location_scale_random_scale_slope,
    simulate_gazepoint_hierarchical_location_scale_random_scale_slope,
)

data = simulate_gazepoint_hierarchical_location_scale_random_scale_slope(
    n_groups=24,
    observations_per_group=10,
    seed=42,
)

fit = fit_gazepoint_hierarchical_location_scale_random_scale_slope(
    data,
    outcome_col="outcome",
    group_col="participant",
    mean_cols=["x"],
    scale_cols=["x"],
    scale_random_slope_col="x",
    quadrature_points=5,
)
```

The fitted object reports fixed location and log-scale coefficients, the three random-effect standard deviations and correlations, the full covariance matrix, convergence diagnostics, empirical-Bayes group effects, deterministic design metadata and the canonical data hash used for reproducibility.

## Prediction semantics

```python
from gpbiometricspy.hierarchical_location_scale_random_scale_slope import (
    predict_gazepoint_hierarchical_location_scale_random_scale_slope,
)

pred = predict_gazepoint_hierarchical_location_scale_random_scale_slope(
    fit,
    data.head(),
)
```

For groups seen during fitting, conditional predictions use empirical-Bayes estimates for the location intercept, log-scale intercept and log-scale slope. For unseen groups, the method deliberately returns population-level predictions rather than inventing group effects.

The prediction table includes `random_log_scale_effect`, which equals the empirical-Bayes log-scale intercept plus the empirical-Bayes log-scale slope multiplied by the encoded slope predictor.

## Reproducibility certificate

```python
from gpbiometricspy.hierarchical_location_scale_random_scale_slope import (
    create_gazepoint_hierarchical_location_scale_random_scale_slope_certificate,
    validate_gazepoint_hierarchical_location_scale_random_scale_slope_certificate,
)

certificate = create_gazepoint_hierarchical_location_scale_random_scale_slope_certificate(fit)
assert validate_gazepoint_hierarchical_location_scale_random_scale_slope_certificate(
    fit,
    certificate,
)
```

Certificates bind the model version, canonical data fingerprint, row-order-invariant empirical-Bayes random-effects fingerprint, design terms, fitted coefficients, covariance matrix and quadrature setting. Certificates fail closed for non-converged fits.

## Synthetic known-truth validation

The simulator stores its generating parameters in `data.attrs["known_truth"]`, including the fixed effects, full random-effect covariance matrix, random-effect standard deviations and correlations, and seed. The test suite uses this simulator for deterministic known-truth recovery checks in addition to derivative/Hessian finite-difference validation.

## Interpretation boundary

The random log-scale slope estimates **heterogeneity in an association with conditional residual variability**. It is not automatically a variability phenotype, a stable participant trait, an artifact score, or evidence that a sensor is valid or invalid.

This method by itself does **not**:

- identify or correct eye-tracking, motion or physiological artifacts;
- establish sensor validity or reliability;
- perform sensor-validity weighting;
- identify causal effects;
- infer emotion, stress, trust, preference, cognition, diagnosis or another latent state; or
- support simultaneous location-and-scale random slopes, multiple random slopes, crossed random effects, mixture distributions or Bayesian priors.

Those claims require additional design assumptions, validation evidence or different model families.
