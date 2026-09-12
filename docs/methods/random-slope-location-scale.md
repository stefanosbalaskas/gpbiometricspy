# Random-slope hierarchical location–scale modelling

`gpbiometricspy` includes an additive Python-native Gaussian hierarchical location–scale model with **one participant/group-specific random slope in the location equation**. It extends the certified random-intercept location–scale family without changing the frozen 406-export `gpbiometrics 2.0.0` parity surface.

## Model

For observation *i* in group *j*:

\[
y_{ij} \sim \mathcal{N}(\mu_{ij}, \sigma_{ij}),
\]

\[
\mu_{ij} = x_{ij}^{\top}\beta + u_{0j} + u_{1j}r_{ij},
\]

\[
\log(\sigma_{ij}) = z_{ij}^{\top}\gamma + v_j,
\]

with

\[
(u_{0j},u_{1j},v_j)^{\top} \sim \mathcal{N}(0,\Sigma).
\]

The full positive-definite **3 × 3 covariance matrix** `Σ` is estimated through a Cholesky parameterisation. It allows correlation between the location intercept, location slope, and log-scale intercept.

The group marginal likelihood is evaluated with **three-dimensional adaptive Gauss–Hermite quadrature** centred on the participant/group posterior mode.

## What the random slope means

The random slope represents **between-participant/group heterogeneity in the conditional association between a numeric repeated-measures predictor and the outcome location**. It is not a causal effect and should not be interpreted as evidence that the predictor caused the observed within-person change.

The current implementation deliberately supports **one random slope in the location equation only**. Additional random slopes, random slopes in the log-scale equation, crossed random effects, skewed outcome families, mixtures, and Bayesian priors remain outside this method.

## Identifiability guardrails

`random_slope_col` must:

- be numeric;
- also appear in `mean_cols` as a fixed effect, preserving the hierarchical principle;
- contain finite variation in the analysis sample;
- vary within **every** participant/group; and
- be supported by at least six participant/groups for covariance estimation.

The same numeric encoding used for the fixed mean effect is reused for the random slope. With the default `standardize_numeric=True`, the reported random-slope variance is therefore on the standardised predictor scale.

## Fit the model

```python
from gpbiometricspy.hierarchical_location_scale_random_slope import (
    fit_gazepoint_hierarchical_location_scale_random_slope,
    simulate_gazepoint_hierarchical_location_scale_random_slope,
)

# Fully synthetic known-truth data.
data = simulate_gazepoint_hierarchical_location_scale_random_slope(
    n_groups=24,
    observations_per_group=10,
    seed=21,
)

fit = fit_gazepoint_hierarchical_location_scale_random_slope(
    data,
    outcome_col="outcome",
    group_col="participant",
    mean_cols=["x"],
    scale_cols=["x"],
    random_slope_col="x",
    quadrature_points=3,
)
```

The fitted object reports:

- fixed mean and log-scale coefficients;
- random-intercept, random-slope, and log-scale-intercept standard deviations;
- the three pairwise random-effect correlations;
- the complete 3 × 3 covariance matrix;
- marginal log likelihood and optimizer diagnostics;
- empirical-Bayes participant/group effects and uncertainty summaries;
- immutable model metadata and parameter state.

## Prediction semantics

```python
from gpbiometricspy.hierarchical_location_scale_random_slope import (
    predict_gazepoint_hierarchical_location_scale_random_slope,
)

pred = predict_gazepoint_hierarchical_location_scale_random_slope(
    fit,
    data.head(),
)
```

For groups seen during fitting, conditional predictions use empirical-Bayes estimates of `u0`, `u1`, and `v`. The random contribution to outcome location is

\[
u_{0j} + u_{1j}r_{ij}.
\]

For unseen groups, predictions are explicitly labelled `population_unseen_group` and set all random effects to zero. Setting `include_random_effects=False` returns population-level predictions for every row.

Prediction output includes the encoded `random_slope_value` and the combined `random_location_effect`, making the participant-specific contribution inspectable rather than hidden.

## Summaries and reproducibility certificates

```python
from gpbiometricspy.hierarchical_location_scale_random_slope import (
    create_gazepoint_hierarchical_location_scale_random_slope_certificate,
    summarize_gazepoint_hierarchical_location_scale_random_slope,
    validate_gazepoint_hierarchical_location_scale_random_slope_certificate,
)

summary = summarize_gazepoint_hierarchical_location_scale_random_slope(fit)
certificate = create_gazepoint_hierarchical_location_scale_random_slope_certificate(fit)
assert validate_gazepoint_hierarchical_location_scale_random_slope_certificate(
    fit, certificate
)
```

Certificates bind the canonical analysis-data fingerprint, fixed-effect terms and estimates, the selected random-slope variable, the full random-effect covariance matrix, quadrature specification, convergence state, and a **row-order-invariant SHA-256 fingerprint of the empirical-Bayes random-effects table** used for conditional prediction. Tampering with fitted random effects invalidates the certificate; row reordering does not.

## Synthetic known-truth validation

The bundled simulator generates data from the same Gaussian location–scale random-slope family and stores the generating parameters in `DataFrame.attrs["known_truth"]`. It is intended for method testing, recovery studies, examples, and sensitivity work.

Synthetic known-truth validation is not empirical/native-data validation. Recovery depends on sample size, repeated-measures spread, random-slope variance, correlation structure, quadrature resolution, and optimizer behaviour.

## Numerical scope

The method uses analytic participant-level posterior gradients and Hessians for the three-dimensional latent state and adaptive Gauss–Hermite quadrature for marginalisation. Defensive numerical paths include pseudoinverse fallbacks, posterior-Hessian repair, eigenvalue-based covariance repair, and Cholesky fallback for adaptive quadrature.

Higher quadrature resolution increases cost rapidly because three-dimensional quadrature uses `points³` nodes per group. The public interface therefore constrains `quadrature_points` to 3–11 rather than inheriting the wider two-dimensional range.

## Scientific boundary

This model estimates **distributional heterogeneity**. It does not by itself:

- identify or correct eye-tracking or physiological artifacts;
- establish sensor validity, reliability, or signal quality;
- perform sensor-validity weighting;
- establish within-person or between-person causal effects;
- infer emotion, stress, trust, preference, cognition, diagnosis, or other latent states; or
- justify interpreting empirical-Bayes random effects as error-free participant traits.

The random slope should be reported as model-based heterogeneity in an association under the specified Gaussian hierarchical model, together with the predictor scale, covariance specification, convergence diagnostics, and repeated-measures design.