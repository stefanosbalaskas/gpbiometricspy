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

**Exact-main certified.** PR **#133** introduced the method from qualified head `52334c6ac4ecfb344abbd9e6d8b04570b86d721a` and was squash-merged at `f4ee2c7ac73c062c53682cf8be67f40b8768c63a`. Its first exact-main branch audit exposed one nondeterministically uncovered private-core loop-exhaustion edge. PR **#134** added a direct test-only regression for that edge, changed no production code, scientific semantics, or structural-debt entry, and was squash-merged to the formally certified default-branch SHA `33175e1d0507109c2af1f526b460f0f3ba6a7063` (tree `37a038b74c8e4cf5a547105b027f588cbc307440`). Formal certification checkpoint: PR #134 comment `5676677748`.

Fresh exact-main Tests #626 is **12/12 platform/Python lanes green**. Canonical Ubuntu 24.04.5 / CPython 3.12.14 evidence is **824/824 tests**, **14,757/14,757 statements**, Ruff and compile clean, with frozen R parity unchanged at **406/406 exports and 0 pending**.

Exact-main Branch Coverage #406 (run `34941909652`) records **7,025/7,044 raw branches = 99.7303%**, with exactly **19** audited structural/caller-dominated residual arcs and **0 unexpected**, **0 stale**, and **0 unaudited** branch debt. Audited accounting is **7,044/7,044 = 100.0000%** without redefining raw branch coverage. The exact-main evidence artifact is `10385841209`, SHA-256 `621c8d8c724323426af32c7d7bb5f3631a0b5a7188422b99e7647ed8036a84d4`.

Docs #389 also passes documentation generation, `mkdocs build --strict`, and the main-only GitHub Pages deployment on the certified SHA. The method remains additive Python-native functionality outside the frozen `gpbiometrics 2.0.0` 406-export parity surface.
