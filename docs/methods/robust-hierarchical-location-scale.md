# Robust Student-t hierarchical location–scale modelling

`gpbiometricspy.robust_hierarchical_location_scale` extends the package's hierarchical location–scale methods to a heavy-tailed conditional outcome model. It is an additive Python-native method and remains separate from the frozen 406-function `gpbiometrics` R semantic-parity contract.

## Model

For observation *i* from participant/group *j*,

\[
y_{ij} \sim t_{\nu}(\mu_{ij}, \sigma_{ij}),
\]

with

\[
\mu_{ij}=x_{ij}^{\mathsf T}\beta+u_j,
\qquad
\log \sigma_{ij}=z_{ij}^{\mathsf T}\gamma+v_j,
\]

and correlated participant/group random intercepts

\[
(u_j,v_j)^{\mathsf T}\sim\mathcal{N}(0,\Sigma).
\]

The degrees of freedom \(\nu\) are estimated jointly with the fixed effects and random-effect covariance parameters, subject to \(2.05 \le \nu \le 200\). The same bounds are enforced by the known-truth simulator so simulated and fitted parameter spaces remain aligned. The lower bound keeps the conditional variance finite. Marginal group likelihoods are evaluated with two-dimensional adaptive Gauss–Hermite quadrature.

## Why Student-t?

A Gaussian location–scale model can let a small number of extreme outcomes exert disproportionate influence on both location and residual-scale estimation. The Student-t likelihood supplies a directly estimated heavy-tail parameter instead of requiring the analyst to delete observations merely because they are extreme.

That robustness is distributional, not diagnostic. The model does **not** determine whether an extreme observation is a motion artifact, hardware failure, valid physiological response, or any other substantive mechanism.

## Minimal example

```python
from gpbiometricspy.robust_hierarchical_location_scale import (
    fit_gazepoint_robust_hierarchical_location_scale,
    predict_gazepoint_robust_hierarchical_location_scale,
    simulate_gazepoint_robust_hierarchical_location_scale,
)

data = simulate_gazepoint_robust_hierarchical_location_scale(
    degrees_of_freedom=5,
    seed=42,
)

fit = fit_gazepoint_robust_hierarchical_location_scale(
    data,
    outcome_col="outcome",
    group_col="participant",
    mean_cols=["x"],
    scale_cols=["x"],
    quadrature_points=7,
)

pred = predict_gazepoint_robust_hierarchical_location_scale(fit, data.head())
```

The same fail-closed design-matrix rules as the Gaussian model apply: the outcome and group identifiers cannot be reused as fixed-effect predictors, numeric predictors can be standardized, and unseen categorical levels are rejected at prediction time.

## Scale is not standard deviation

For this parameterization, `predicted_scale` is the Student-t scale parameter \(\sigma\), not the residual standard deviation. Because the fitted model constrains \(\nu>2\), the implied conditional residual standard deviation is

\[
\operatorname{SD}(Y\mid\cdot)
=\sigma\sqrt{\frac{\nu}{\nu-2}}.
\]

`predict_gazepoint_robust_hierarchical_location_scale()` therefore returns both `predicted_scale` and `predicted_residual_sd`, together with the fitted `degrees_of_freedom`.

## Prediction semantics

For groups observed during fitting, conditional predictions use empirical-Bayes location and log-scale random-effect summaries. An unseen group has no estimated group-specific random effect, so it receives an explicit population-level prediction and is labelled `population_unseen_group`. Setting `include_random_effects=False` always requests population-level prediction.

## Reproducibility certificate

`create_gazepoint_robust_hierarchical_location_scale_certificate()` binds the model version, canonical input-data fingerprint, mean and scale terms, fitted coefficients, random-effect covariance parameters, fitted degrees of freedom, quadrature resolution, the canonical empirical-Bayes random-effects table fingerprint, and an explicit converged-fit state into a SHA-256 certificate.

The random-effects fingerprint is row-order invariant because the table is canonically sorted by group before hashing. Changing a fitted empirical-Bayes random effect therefore invalidates a previously issued certificate, while harmless row reordering does not.

Certificate creation is fail-closed. A result retained with `require_convergence=False` for diagnostic inspection cannot be certified unless the optimizer actually reports convergence. Malformed fitted metadata that would make certificate reconstruction incomplete is rejected by validation rather than being treated as valid evidence. Changing the fitted degrees of freedom, coefficients, covariance parameters, or empirical-Bayes state invalidates the certificate.

## Validation strategy

The method tests include a finite-difference audit of the analytic gradient and Hessian used for the participant-level posterior mode, deterministic known-truth Student-t simulation, exact lower/upper degrees-of-freedom boundary checks, scale-to-standard-deviation prediction checks, reserved-column leakage guards, unseen-group prediction semantics, random-effects certificate binding, row-order-invariant certificate hashing, malformed-metadata rejection, and certificate tamper detection. Repository-wide branch-coverage evidence is treated separately from substantive statistical validation.

## Scientific boundaries

This method estimates heavy-tailed distributional heterogeneity conditional on its stated Student-t specification. It does **not**:

- classify or correct eye-tracking or physiological artifacts;
- convert residual scale into sensor-quality or validity weights;
- establish that a low fitted \(\nu\) proves contamination or measurement failure;
- identify causal effects; or
- infer latent psychological, emotional, attentional, or clinical states.

This tranche uses correlated random intercepts only. Random slopes, crossed random effects, skewed/heavy-tail families beyond symmetric Student-t, mixture models, and Bayesian priors remain outside its current scope.
