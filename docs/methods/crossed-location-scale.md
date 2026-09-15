# Crossed participant–item hierarchical location–scale modelling

This Python-native method extends the location–scale family to repeated-measures designs in which observations are **crossed by participant and item/stimulus**. It is additive to the frozen `gpbiometrics 2.0.0` parity surface and does not change the 406-export R contract.

## Model

For observation \(n\), participant \(p[n]\), and item \(i[n]\):

\[
y_n \mid u_{p[n]}, v_{p[n]}, a_{i[n]}, c_{i[n]}
\sim \mathcal{N}(\mu_n, \sigma_n^2),
\]

\[
\mu_n = x_n^\top\beta + u_{p[n]} + a_{i[n]},
\qquad
\log \sigma_n = z_n^\top\gamma + v_{p[n]} + c_{i[n]}.
\]

Participant effects follow

\[
(u_p, v_p)^\top \sim \mathcal{N}(0, \Sigma_{participant}),
\]

and item effects follow

\[
(a_i, c_i)^\top \sim \mathcal{N}(0, \Sigma_{item}).
\]

The participant and item latent families are independent of one another, while each 2 × 2 covariance matrix estimates the correlation between **location heterogeneity** and **log-scale heterogeneity** within that factor.

This first crossed implementation uses random intercepts in both equations. Crossed random slopes are intentionally outside its current scope.

## Why crossed effects matter

Eye-tracking and multimodal psychophysiology experiments commonly collect many observations from each participant and expose the same stimuli, trials, scenes, advertisements, interfaces, or tasks to multiple participants. Treating participant as the only grouping factor can leave stimulus/item heterogeneity unmodelled. The crossed model represents both sources of clustering in the conditional mean and residual scale without treating item effects as fixed nuisance dummies.

## Estimation

Unlike the existing one-group models, crossed participant and item effects cannot be integrated independently group by group. The implementation therefore uses a **joint Laplace approximation** over the complete latent field.

With \(P\) participants and \(I\) items, the latent dimension is

\[
d = 2(P + I).
\]

For the posterior mode \(b^*\) and joint log density \(h(b)\), the marginal log likelihood is approximated as

\[
\log L \approx h(b^*) + \frac{d}{2}\log(2\pi)
- \frac{1}{2}\log\left| -H(b^*) \right|.
\]

The latent mode is obtained with damped Newton updates using the analytic gradient and Hessian. The outer model parameters are optimized with bounded L-BFGS-B. Participant and item covariance matrices are parameterized through positive standard deviations and a transformed correlation, so invalid covariance matrices fail closed.

The first implementation uses a dense latent Hessian for deterministic, auditable behaviour. Dense factorization has roughly cubic cost in the latent dimension, so `max_latent_dimension=400` is a deliberate default safety ceiling rather than a claim of scalability to arbitrarily large crossed designs.

## Design requirements

The fitter rejects specifications that do not satisfy the minimum identification and connectivity contract:

- `outcome_col`, `participant_col`, and `item_col` must be distinct;
- fixed-effect predictors may not reuse any of those role columns;
- at least four participant levels and four item levels must remain after complete-case filtering;
- every participant must contribute observations on at least two distinct items;
- every item must be observed for at least two distinct participants;
- the participant × item bipartite incidence graph must be connected;
- numeric predictors must be finite after filtering; and
- the latent dimension must not exceed the configured dense-Laplace safety ceiling.

These checks prevent disconnected or trivially unreplicated crossed structures from being silently optimized as if they were well identified.

## Basic use

```python
from gpbiometricspy.hierarchical_location_scale_crossed import (
    fit_gazepoint_crossed_hierarchical_location_scale,
    predict_gazepoint_crossed_hierarchical_location_scale,
    simulate_gazepoint_crossed_hierarchical_location_scale,
)

data = simulate_gazepoint_crossed_hierarchical_location_scale(
    n_participants=12,
    n_items=10,
    seed=2026,
)

fit = fit_gazepoint_crossed_hierarchical_location_scale(
    data,
    outcome_col="outcome",
    participant_col="participant",
    item_col="item",
    mean_cols=["mean_predictor"],
    scale_cols=["scale_predictor"],
)
```

The fitted object reports fixed effects, participant and item covariance parameters, the approximate marginal log likelihood, diagnostics, immutable parameter/covariance arrays, and separate participant/item empirical-Bayes mode tables with approximate posterior standard deviations.

## Prediction semantics

Prediction distinguishes whether participant and item levels were observed during fitting. With `include_random_effects=True` and the default `unknown_levels="population"`:

- seen participant + seen item → `conditional_participant_item`;
- unseen participant + seen item → `population_participant_conditional_item`;
- seen participant + unseen item → `conditional_participant_population_item`;
- unseen participant + unseen item → `population_participant_item`.

Setting `include_random_effects=False` produces `population_fixed_effects` predictions. Setting `unknown_levels="error"` makes any unseen participant or item fail closed instead of silently falling back to a population contribution.

## Reproducibility certificate

`create_gazepoint_crossed_hierarchical_location_scale_certificate()` binds the model version, canonical training-data hash, role columns, dimensions, terms, coefficients, participant/item covariance matrices, random-effect-table hashes, parameter vector, marginal likelihood, and approximation label into a deterministic SHA-256 certificate.

`validate_gazepoint_crossed_hierarchical_location_scale_certificate()` canonicalizes JSON key ordering before comparison, so semantically identical payload ordering does not invalidate a genuine certificate while any substantive payload change does.

## Interpretation boundary

The participant and item random effects represent modelled association heterogeneity. They are **not** automatic measurements of participant traits, stimulus quality, artifact burden, sensor validity, attention, emotion, stress, trust, preference, cognition, diagnosis, or causal effects.

The model does not:

- detect or correct eye-tracking or physiological artifacts;
- establish measurement validity or reliability;
- assign sensor-validity weights;
- justify removing participants or stimuli solely because an empirical-Bayes effect is large;
- establish causal effects; or
- infer latent psychological states from physiological or gaze signals.

## Validation status

The crossed participant–item random-intercept method is **exact-main certified**. It was introduced and certified through PR **#124**, merge SHA `eb8c737f93e952f7bec0e6d7958336f1ecf469f5`. Its scientific implementation remains unchanged by the later random-slope extensions.

The method-specific source module is fully exercised at **444/444 statements** and **168/168 branches**. The frozen `gpbiometrics 2.0.0` export contract remains **406/406 implemented with 0 pending**.

Repository-wide test and coverage totals evolve as new additive Python-native methods are introduced. For the current exact-main package baseline, use the [Methods overview](index.md) and [Deep validation](../deep-validation.md) rather than treating historical package-wide totals on an individual method page as live status.

Certification is based on fresh post-merge evidence from the exact merge SHA; pre-merge qualification is not substituted for exact-main evidence.