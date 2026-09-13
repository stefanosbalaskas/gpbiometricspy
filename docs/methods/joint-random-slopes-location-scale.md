# Joint random-slope hierarchical location–scale modelling

This Python-native method extends the Gaussian hierarchical location–scale family with **one participant/group-specific numeric slope in the location equation and one participant/group-specific numeric slope in the log-scale equation**.

The random-effects vector is

`(location intercept, location slope, log-scale intercept, log-scale slope)`

with a full positive-definite **4 × 4 covariance matrix**. Group marginal likelihoods are evaluated with **four-dimensional adaptive Gauss–Hermite quadrature**.

## Model

For observation `i` in group `g`:

- `y_ig ~ Normal(mu_ig, sigma_ig)`
- `mu_ig = X_ig beta + u0_g + u1_g rL_ig`
- `log(sigma_ig) = Z_ig gamma + v0_g + v1_g rS_ig`

where `(u0_g, u1_g, v0_g, v1_g)` follows a zero-mean multivariate Gaussian distribution with an unrestricted positive-definite covariance matrix.

The location and scale random-slope predictors may be the same observed variable or different variables. Each must be numeric, appear as a fixed effect in the corresponding equation, and vary within every participant/group. The implementation requires at least **eight groups** before estimating the 4 × 4 covariance.

## Fit the model

```python
from gpbiometricspy.hierarchical_location_scale_joint_random_slopes import (
    fit_gazepoint_hierarchical_location_scale_joint_random_slopes,
    simulate_gazepoint_hierarchical_location_scale_joint_random_slopes,
)

data = simulate_gazepoint_hierarchical_location_scale_joint_random_slopes(
    n_groups=24,
    observations_per_group=10,
    seed=42,
)

fit = fit_gazepoint_hierarchical_location_scale_joint_random_slopes(
    data,
    outcome_col="outcome",
    group_col="participant",
    mean_cols=["x_location"],
    scale_cols=["x_scale"],
    location_random_slope_col="x_location",
    scale_random_slope_col="x_scale",
    quadrature_points=3,
)
```

The fitted object reports fixed location/log-scale coefficients, four random-effect standard deviations, the full covariance and correlation matrices, empirical-Bayes group effects, convergence diagnostics, deterministic design metadata, and a canonical data fingerprint.

## Why the quadrature default is 3

Four-dimensional quadrature grows as `quadrature_points ** 4`: 3 points generate 81 nodes per group, 5 points generate 625, and 7 points generate 2,401. The default is therefore **3** and the supported range is **3–7**.

The default is a computational policy, not a claim that three points are universally sufficient. Researchers should examine higher-node sensitivity when sample size, covariance complexity, or inferential stakes warrant it and report the setting used.

## Prediction semantics

```python
from gpbiometricspy.hierarchical_location_scale_joint_random_slopes import (
    predict_gazepoint_hierarchical_location_scale_joint_random_slopes,
)

pred = predict_gazepoint_hierarchical_location_scale_joint_random_slopes(
    fit,
    data.head(),
)
```

For groups seen during fitting, conditional predictions use empirical-Bayes estimates of all four random effects. For unseen groups, predictions deliberately revert to the population model rather than inventing group effects.

The prediction table reports both `random_location_effect` and `random_log_scale_effect`, together with the encoded values of each random-slope predictor and the source of the random effect.

## Reproducibility certificate

```python
from gpbiometricspy.hierarchical_location_scale_joint_random_slopes import (
    create_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate,
    validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate,
)

certificate = create_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(fit)
assert validate_gazepoint_hierarchical_location_scale_joint_random_slopes_certificate(
    fit,
    certificate,
)
```

Certificates bind the model version, canonical data fingerprint, row-order-invariant empirical-Bayes fingerprint, both random-slope columns, design terms, fixed coefficients, covariance matrix, and quadrature setting. Certificate creation fails closed for non-converged fits.

## Synthetic known-truth validation

The simulator stores generating coefficients, the complete 4 × 4 random-effect covariance and correlation matrices, random-effect standard deviations, and seed in `data.attrs["known_truth"]`.

The dedicated test suite validates analytic gradients/Hessians against central finite differences and includes deterministic known-truth signal-recovery checks. These are synthetic method-validation exercises; they are not empirical sensor-validity evidence.

## Interpretation boundary

The location random slope estimates **heterogeneity in an observed association with the conditional mean**. The log-scale random slope estimates **heterogeneity in an observed association with conditional residual variability**. Neither is automatically a causal effect, stable trait, variability phenotype, artifact score, or sensor-validity measure.

This method by itself does **not**:

- identify or correct eye-tracking, motion, or physiological artifacts;
- establish sensor validity or reliability;
- perform sensor-validity weighting;
- identify causal effects;
- infer emotion, stress, trust, preference, cognition, diagnosis, or another latent state; or
- support additional random slopes, crossed random effects, mixture distributions, or Bayesian priors.

Those claims require additional design assumptions, validation evidence, or different model families.
