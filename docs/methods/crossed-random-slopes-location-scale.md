# Crossed participant–item random-slope location–scale modelling

This development method extends the crossed participant × item/stimulus Gaussian location–scale model with **one location random slope for each crossed factor**.

For observation \(n\), participant \(p[n]\), and item \(i[n]\),

\[
y_n \sim \mathcal{N}(\mu_n,\sigma_n^2),
\]

with

\[
\mu_n =
x_n^\top\beta
+ u_{0,p[n]}
+ u_{1,p[n]} r^{(p)}_n
+ v_{0,i[n]}
+ v_{1,i[n]} r^{(i)}_n,
\]

and

\[
\log(\sigma_n) =
z_n^\top\gamma
+ u_{2,p[n]}
+ v_{2,i[n]}.
\]

The participant random-effects block is

\[
(u_{0,p},u_{1,p},u_{2,p})^\top
\sim \mathcal{N}(0,\Sigma_p),
\]

and the item/stimulus block is

\[
(v_{0,i},v_{1,i},v_{2,i})^\top
\sim \mathcal{N}(0,\Sigma_i).
\]

Each covariance matrix is an unrestricted positive-definite **3 × 3** matrix represented through a Cholesky parameterization. Participant and item random-effect families are independent of one another, while correlations among location intercept, location slope, and log-scale intercept are estimated within each factor.

## Why this extension exists

Repeated eye-tracking and psychophysiology experiments frequently cross people with stimuli, trials, scenes, products, interfaces, or tasks. A crossed random-intercept model allows baseline outcome and residual-scale heterogeneity for both factors, but it still assumes the conditional association with a repeated-measures predictor is identical across every participant and every item.

This extension allows one numeric association to vary across participants and one numeric association to vary across items while retaining crossed residual-scale heterogeneity.

The method is deliberately narrower than a general mixed-model grammar. In this tranche:

- each crossed factor receives one **location** random slope;
- each crossed factor retains one location random intercept and one log-scale random intercept;
- there are no random slopes in the log-scale equation;
- there is no participant × item interaction random effect;
- the conditional response distribution remains Gaussian.

## Identification and fail-closed design

The fitter rejects specifications that do not meet the declared design requirements.

- At least **six participants** and **six items** are required before 3 × 3 covariance estimation.
- Every participant must span at least two items, and every item must span at least two participants.
- The participant × item incidence graph must be connected.
- `participant_random_slope_col` must be numeric, must also appear in `mean_cols`, and must vary within every participant.
- `item_random_slope_col` must be numeric, must also appear in `mean_cols`, and must vary within every item.
- The two random-slope variables may be the same observed variable or different variables if both design conditions are satisfied.
- Outcome, participant, and item role columns must remain distinct and cannot be reused as predictors.
- A dense latent-dimension ceiling fails closed before optimization when the requested crossed field is too large.

Numeric random-slope values use the same fitted encoding and standardization as their corresponding fixed mean effects. This preserves the hierarchical principle: a random slope is not fitted for a predictor that is absent from the population-level mean equation.

## Joint Laplace approximation

Crossed participant and item effects cannot be integrated independently by factor. The implementation therefore fits the complete crossed latent field jointly.

With \(P\) participants and \(I\) items, the latent dimension is

\[
3(P+I).
\]

For every observation, the analytic posterior gradient and Hessian include:

- participant and item location-intercept contributions;
- participant and item location-slope contributions;
- participant and item log-scale-intercept contributions;
- all observation-induced cross-curvature among those active latent terms; and
- the two Gaussian 3 × 3 random-effect priors.

A damped Newton solver locates the joint latent posterior mode. The marginal log likelihood is then approximated with a dense joint Laplace correction. Outer covariance and fixed-effect parameters are optimized with bounded L-BFGS-B.

Because the Hessian is dense, this is intentionally not presented as a large-scale crossed-effects engine. `max_latent_dimension` is an explicit computational guardrail, not a claim that every design below the ceiling will be inexpensive.

## Prediction semantics

`predict_gazepoint_crossed_hierarchical_location_scale_random_slopes()` keeps population and conditional prediction separate.

For a participant or item observed during training, conditional prediction adds that factor's empirical-Bayes location intercept, location slope times the encoded slope predictor, and log-scale intercept.

For an unseen participant or item, `unknown_levels="population"` assigns a zero random effect for that factor. This is a population-level prediction for the unseen factor, not an estimated random effect.

`unknown_levels="error"` instead fails closed whenever conditional prediction encounters an unseen participant or item.

Prediction output records whether each factor was observed and distinguishes:

- conditional participant + conditional item;
- conditional participant + population item;
- population participant + conditional item;
- population participant + population item; and
- fixed-effects-only prediction when random effects are disabled.

## Reproducibility certificates

A converged fit can be bound to a deterministic SHA-256 certificate containing:

- model and schema identity;
- training-frame digest;
- role and random-slope column identities;
- fixed-effect terms and coefficients;
- participant and item covariance matrices;
- marginal log likelihood;
- empirical-Bayes random-effect table digests;
- complete fitted parameter vector; and
- declared approximation identity.

Certificate validation canonicalizes JSON key ordering and fails closed on payload or digest mutation. A non-converged fit cannot be certified.

## Scientific interpretation boundary

The random slopes estimate **heterogeneity in conditional associations**.

They do **not** by themselves:

- identify causal effects;
- prove a stable participant or stimulus trait;
- classify or correct eye-tracking or physiological artifacts;
- establish sensor validity or reliability;
- create sensor-validity weights;
- infer emotion, stress, trust, preference, cognition, diagnosis, or another latent psychological/clinical state; or
- justify treating residual-scale random effects as measurement quality.

The log-scale equation models conditional residual heterogeneity under the stated Gaussian model. The location slopes model association heterogeneity conditional on the specified fixed and random effects. Scientific interpretation remains constrained by experimental design, measurement validity, and the assumptions of the fitted model.

## Example

```python
from gpbiometricspy.hierarchical_location_scale_crossed_random_slopes import (
    fit_gazepoint_crossed_hierarchical_location_scale_random_slopes,
    predict_gazepoint_crossed_hierarchical_location_scale_random_slopes,
    simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes,
)

data = simulate_gazepoint_crossed_hierarchical_location_scale_random_slopes(
    n_participants=8,
    n_items=8,
    seed=123,
)

fit = fit_gazepoint_crossed_hierarchical_location_scale_random_slopes(
    data,
    "outcome",
    "participant",
    "item",
    participant_random_slope_col="participant_slope_predictor",
    item_random_slope_col="item_slope_predictor",
    mean_cols=[
        "participant_slope_predictor",
        "item_slope_predictor",
    ],
    scale_cols=["scale_predictor"],
    standardize_numeric=False,
)

pred = predict_gazepoint_crossed_hierarchical_location_scale_random_slopes(
    fit,
    data.iloc[:10],
)
```

## Current validation status

This page documents a **development candidate**. The last independently certified scientific baseline remains PR **#127**, exact-main SHA `e8721b945954f75c98d1d6e5f5b57ce4db9a77dc`, until this candidate completes exact-head qualification, merge-object verification, and fresh exact-main certification.

The candidate was mathematically preflighted by comparing its analytic latent gradient and Hessian against central finite differences and by fitting a minimum 6 × 6 synthetic crossed design. Focused local validation measured the new module at **435/435 statements and 148/148 branches**. Repository CI remains authoritative for the final denominator, full-suite coverage, parity, documentation, interoperability, CodeQL, packaging, and readiness evidence.

The frozen **406/406** `gpbiometrics 2.0.0` R-parity export surface is unchanged.
