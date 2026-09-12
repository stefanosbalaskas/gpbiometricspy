# Python-native methods

`gpbiometricspy` preserves a completed **406/406** semantic-parity surface against the frozen `gpbiometrics 2.0.0` R reference. The pages in this section document **additive Python-native methodological extensions** that sit outside that frozen export contract.

Keeping these methods separate is deliberate: new methodological research should be discoverable and publishable without blurring the distinction between R-parity work and later Python-native development.

## Available method

### Hierarchical location–scale modelling

The current development line adds a Gaussian hierarchical location–scale model that jointly estimates:

- a fixed-effects **mean equation**;
- a fixed-effects **log residual-scale equation**;
- correlated participant/group random intercepts in both equations;
- group marginal likelihoods using **two-dimensional adaptive Gauss–Hermite quadrature**;
- empirical-Bayes summaries for seen groups;
- explicit population-level prediction semantics for unseen groups;
- deterministic design encoding, convergence diagnostics and reproducibility certificates.

[Open the hierarchical location–scale guide →](hierarchical-location-scale.md)

## Validation boundary

On canonical development `main` at `d1e397c4d73819085584c924d8eb1a069f4fba3b`, the repository passed **662 tests**, **10,847/10,847 statements = 100.00%**, **5,747/5,766 raw branches = 99.6705%**, and an audited 19-arc structural-debt contract with **0 unexpected, 0 stale and 0 unaudited branch debt**. The exact merged SHA completed **14/14 push workflow families successfully**.

These are **development-main** metrics. Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. In particular, the current hierarchical location–scale implementation does **not**:

- identify or correct motion artifacts;
- establish sensor validity or reliability;
- perform sensor-validity weighting;
- identify causal effects;
- infer emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

Random slopes, crossed random effects, non-Gaussian outcomes, Bayesian priors and causal interpretation are outside the current hierarchical location–scale tranche.
