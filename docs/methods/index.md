# Python-native methods

`gpbiometricspy` preserves a completed **406/406** semantic-parity surface against the frozen `gpbiometrics 2.0.0` R reference. The pages in this section document **additive Python-native methodological extensions** that sit outside that frozen export contract.

Keeping these methods separate is deliberate: new methodological research should be discoverable and publishable without blurring the distinction between R-parity work and later Python-native development.

## Available methods

### Hierarchical location–scale modelling

The Gaussian hierarchical location–scale model jointly estimates:

- a fixed-effects **mean equation**;
- a fixed-effects **log residual-scale equation**;
- correlated participant/group random intercepts in both equations;
- group marginal likelihoods using **two-dimensional adaptive Gauss–Hermite quadrature**;
- empirical-Bayes summaries for seen groups;
- explicit population-level prediction semantics for unseen groups;
- deterministic design encoding, convergence diagnostics and reproducibility certificates.

[Open the Gaussian hierarchical location–scale guide →](hierarchical-location-scale.md)

### Robust Student-t hierarchical location–scale modelling

The robust extension replaces the conditional Gaussian outcome distribution with a symmetric Student-t distribution while retaining the same mean/log-scale structure and correlated participant/group random intercepts. Its degrees of freedom are estimated jointly with the other model parameters under a finite-variance constraint.

The implementation explicitly distinguishes the Student-t scale parameter from the implied residual standard deviation and treats heavy tails as **distributional robustness**, not evidence that specific observations are artifacts or sensor failures.

[Open the robust Student-t location–scale guide →](robust-hierarchical-location-scale.md)

### Random-slope hierarchical location–scale modelling

The Gaussian random-slope extension adds **one participant/group-specific numeric slope in the location equation** while retaining the log-scale random intercept. The latent state is therefore `(location intercept, location slope, log-scale intercept)` with a full positive-definite 3 × 3 covariance matrix and three-dimensional adaptive Gauss–Hermite quadrature.

The random-slope variable must also enter the fixed mean equation and must vary within every group. This preserves the hierarchical principle and rejects unidentified random-slope specifications before optimization.

[Open the random-slope location–scale guide →](random-slope-location-scale.md)

## Validation boundary

The last exact-main-certified methods baseline is merge SHA `1de9041aace7d5f0fd256b2e9b357308efd7798a` from #116. Fresh push-only certification completed **14/14 workflow families successfully**. Canonical Ubuntu/Python 3.12.14 evidence passed **687/687 tests**, **11,151/11,151 statements = 100.00%**, and retained the frozen export audit at **406/406 with 0 pending**. Exact-main branch coverage was **5,819/5,838 = 99.6745%**, with exactly **19 audited structural arcs**, **0 unexpected**, **0 stale**, and **0 unaudited branch debt**. The exact-main branch-coverage artifact is `10301085630` with digest `sha256:136f75c7edd6769142a62756ea7b7c0a291958d62277f79e0902792d7610ebc9`.

That certification covers the Gaussian and robust Student-t **random-intercept** methods in the certified #116 tree. The random-slope method is a later additive development tranche and must complete its own exact-head and exact-main qualification before being described as certified. Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts; development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. None of the location–scale implementations by itself:

- identifies or corrects motion, eye-tracking, or physiological artifacts;
- establishes sensor validity or reliability;
- performs sensor-validity weighting;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The Gaussian random-intercept method covers Gaussian conditional outcomes. The robust extension adds symmetric Student-t conditional outcomes. The random-slope extension adds one participant/group-specific numeric slope in the Gaussian location equation and treats it as association heterogeneity, not a causal effect or error-free participant trait. Additional random slopes, random slopes in the log-scale equation, crossed random effects, skewed heavy-tail families, mixture models, Bayesian priors and causal interpretation remain outside the current location–scale implementation family.