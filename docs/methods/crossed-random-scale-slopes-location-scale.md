# Crossed participant–item random scale-slope location–scale modelling

This method extends the crossed participant × item/stimulus Gaussian location–scale family with **one log-scale random slope for each crossed factor**. It is designed for repeated eye-tracking and psychophysiology data in which residual dispersion may respond differently to a repeated predictor across people and across items.

For observation \(n\), participant \(p[n]\), and item \(i[n]\),

\[
y_n \sim \mathcal{N}(\mu_n,\sigma_n^2),
\]

with

\[
\mu_n = x_n^\top\beta + u_{0,p[n]} + v_{0,i[n]},
\]

and

\[
\log(\sigma_n) = z_n^\top\gamma
+ u_{1,p[n]} + u_{2,p[n]}r^{(p)}_n
+ v_{1,i[n]} + v_{2,i[n]}r^{(i)}_n.
\]

The participant random-effects block is

\[
(u_{0,p},u_{1,p},u_{2,p})^\top \sim \mathcal{N}(0,\Sigma_p),
\]

and the item/stimulus block is

\[
(v_{0,i},v_{1,i},v_{2,i})^\top \sim \mathcal{N}(0,\Sigma_i).
\]

Each covariance matrix is an unrestricted positive-definite **3 × 3** matrix represented through a Cholesky parameterization. Participant and item random-effect families are independent of one another, while location intercept, log-scale intercept, and log-scale slope may correlate within each factor.

## What this tranche adds

A crossed random-intercept location–scale model allows participant- and item-specific baseline location and residual dispersion. It still assumes that any repeated predictor in the log-scale equation has the same conditional association with residual dispersion for every participant and every item.

This extension allows one numeric log-scale association to vary across participants and one numeric log-scale association to vary across items. The scope is deliberately narrow:

- each crossed factor receives one **location intercept**, one **log-scale intercept**, and one **log-scale random slope**;
- there are no location random slopes in this tranche;
- there is no participant × item interaction random effect;
- participant and item covariance blocks remain separate;
- the conditional response distribution remains Gaussian.

## Identification and fail-closed design

The implementation inherits the crossed participant–item design checks and adds scale-slope-specific guards.

- At least **six participants** and **six items** are required before estimating the trivariate covariance blocks.
- The inherited crossed design preparation requires a usable connected participant × item incidence structure.
- `participant_scale_random_slope_col` must be numeric, must also appear in `scale_cols`, and must vary within every participant.
- `item_scale_random_slope_col` must be numeric, must also appear in `scale_cols`, and must vary within every item.
- Encoded random-slope values use the same fitted centering and scaling as the corresponding population-level scale effect.
- Missing, non-finite, degenerate, or invalid fitted scaling factors fail closed.
- `max_latent_dimension` provides an explicit computational ceiling before dense Laplace optimization begins.

The scale-slope variables may be the same observed variable when both crossed-factor variation requirements are satisfied, or different variables when the design supports both.

## Joint dense Laplace approximation

Participant and item random effects are coupled by the observed crossed incidence pattern, so they are integrated as one latent field. With \(P\) participants and \(I\) items, the latent dimension is

\[
3(P+I).
\]

For every observation, the implementation evaluates the joint log posterior together with analytic gradient and Hessian terms for:

- participant and item location intercepts;
- participant and item log-scale intercepts;
- participant and item log-scale slopes;
- observation-induced cross-curvature among the active latent effects; and
- both Gaussian 3 × 3 random-effect priors.

A damped Newton solver with backtracking locates the joint latent posterior mode. The marginal log likelihood uses a dense Laplace correction, while the outer fixed-effect and covariance parameters are optimized with bounded L-BFGS-B. Non-finite states, non-converged posterior modes, or excessive Hessian stabilization fail closed.

Because this implementation uses a dense Hessian, it is intended for scientifically defensible moderate crossed designs rather than as a claim of large-scale sparse mixed-model performance.

## Prediction semantics

`predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes()` separates conditional and population prediction explicitly.

For an observed participant or item, conditional prediction adds that factor's empirical-Bayes location intercept to the predicted mean and adds its log-scale intercept plus log-scale slope times the encoded slope predictor to the predicted log scale.

For an unseen participant or item, `unknown_levels="population"` assigns a zero random effect for that factor. The result is therefore a population-level prediction for the unseen factor rather than an invented empirical-Bayes effect. `unknown_levels="error"` instead fails closed when an unseen participant or item is encountered.

Prediction output records whether participant and item levels were seen during training and distinguishes conditional participant/item combinations from fixed-effects-only prediction.

## Reproducibility certificates

A converged fit can be bound to a deterministic SHA-256 certificate containing:

- model and schema identity;
- the training-frame digest;
- participant/item and random scale-slope column identities;
- fixed-effect terms and coefficients;
- participant and item covariance matrices;
- marginal log likelihood;
- empirical-Bayes random-effect table digests;
- the complete fitted parameter vector; and
- the declared approximation identity.

Certificate validation canonicalizes JSON key ordering and fails closed on payload or digest mutation. Non-converged fits cannot be certified.

## Scientific interpretation boundary

The random scale slopes estimate **heterogeneity in conditional residual-dispersion associations under the fitted Gaussian model**. They do not, by themselves:

- identify causal effects;
- establish measurement quality or reliability;
- classify or correct eye-tracking or physiological artifacts;
- establish sensor validity;
- create sensor-validity or quality weights;
- prove a stable participant or stimulus trait; or
- identify emotion, stress, trust, preference, cognition, diagnosis, or another latent psychological or clinical state.

Residual dispersion can reflect many processes. Interpretation therefore remains conditional on experimental design, measurement validity, preprocessing, model specification, and the substantive meaning of the scale predictor.

## Example

```python
from gpbiometricspy.hierarchical_location_scale_crossed_random_scale_slopes import (
    fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes,
    predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes,
    simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes,
)

data = simulate_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
    n_participants=8,
    n_items=8,
    repeats=2,
    seed=123,
)

fit = fit_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
    data,
    "outcome",
    "participant",
    "item",
    participant_scale_random_slope_col="participant_scale_predictor",
    item_scale_random_slope_col="item_scale_predictor",
    mean_cols=["mean_predictor"],
    scale_cols=[
        "participant_scale_predictor",
        "item_scale_predictor",
    ],
    standardize_numeric=False,
)

pred = predict_gazepoint_crossed_hierarchical_location_scale_random_scale_slopes(
    fit,
    data.iloc[:10],
)
```

## Validation status

This page documents a **development candidate**, not an exact-main-certified method. The tranche is based directly on certified `main` SHA `1ff7569f7046325b50a15f0138137f6765182c0c`.

The candidate now contains **24 focused tests** and adds **355 statements** plus **130 branches** across the two new source modules. Superseded repaired-head Branch Coverage #396 established the production-source denominator at **14,757 statements** and **7,044 branches** while passing **820/820 tests**; the subsequent three direct numerical-guard tests cover the only four uncovered defensive statements and the two corresponding unexpected branch arcs. Analytic latent gradient/Hessian checks against finite differences remain part of the focused validation. These figures are development evidence only; the immutable GitHub exact-head Branch Coverage and Tests workflows remain authoritative for promotion.

The candidate is additive Python-native functionality. It does not change the frozen **406/406** `gpbiometrics 2.0.0` parity export contract. It must complete the repository's full **14-workflow exact-head qualification** with no evidence waiver before merge is considered.
