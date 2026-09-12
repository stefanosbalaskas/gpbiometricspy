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

## Validation boundary

The Gaussian methods code was exact-main certified at `d1e397c4d73819085584c924d8eb1a069f4fba3b`: **662 tests**, **10,847/10,847 statements = 100.00%**, **5,747/5,766 raw branches = 99.6705%**, and an audited 19-arc structural-debt contract with **0 unexpected, 0 stale and 0 unaudited branch debt**. That exact merged SHA completed **14/14 push workflow families successfully**.

The Student-t method is a later additive development tranche and must carry its own exact-head and exact-main qualification before being described as certified. Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. Neither location–scale implementation by itself:

- identifies or corrects motion or physiological artifacts;
- establishes sensor validity or reliability;
- performs sensor-validity weighting;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The Gaussian method covers Gaussian conditional outcomes. The robust extension adds symmetric Student-t conditional outcomes. Random slopes, crossed random effects, skewed heavy-tail families, mixture models, Bayesian priors and causal interpretation remain outside the current location–scale implementation family.
