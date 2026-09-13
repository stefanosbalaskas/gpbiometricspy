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

The latest merged methods baseline is PR **#119**, merge SHA `0245dd99d2ca8aa44b26c3740f332628f9ba83e4`. Its merge tree is identical to the qualified PR head tree. The PR candidate completed **14/14 exact-head workflow families successfully** before merge.

Fresh exact-main software evidence on the merge SHA passes **694/694 tests**, **11,504/11,504 statements = 100.00%**, and the frozen export audit remains **406/406 with 0 pending**. Exact-main raw branch coverage is **5,909/5,928 = 99.6795%**. All **19** uncovered branch arcs are explicitly audited structural debt, with **0 unexpected**, **0 stale**, and **0 unaudited** branch debt. The random-slope module itself passes **353/353 statements** and **90/90 branches**.

Full exact-main certification is intentionally stricter than source, test, or coverage success alone: it is declared only when every required push workflow for the merge SHA is terminal green. This page therefore distinguishes the **latest merged baseline** from the stronger **fully certified baseline** rather than substituting pre-merge evidence for post-merge evidence.

Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts; development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. None of the location–scale implementations by itself:

- identifies or corrects motion, eye-tracking, or physiological artifacts;
- establishes sensor validity or reliability;
- performs sensor-validity weighting;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The Gaussian random-intercept method covers Gaussian conditional outcomes. The robust extension adds symmetric Student-t conditional outcomes. The random-slope extension adds one participant/group-specific numeric slope in the Gaussian location equation and treats it as association heterogeneity, not a causal effect or error-free participant trait. Additional random slopes, random slopes in the log-scale equation, crossed random effects, skewed heavy-tail families, mixture models, Bayesian priors and causal interpretation remain outside the current location–scale implementation family.
