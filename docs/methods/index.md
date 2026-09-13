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

The Gaussian random-slope extension adds **one participant/group-specific numeric slope in the location equation** while retaining the log-scale random intercept. The latent state is `(location intercept, location slope, log-scale intercept)` with a full positive-definite 3 × 3 covariance matrix and three-dimensional adaptive Gauss–Hermite quadrature.

The random-slope variable must also enter the fixed mean equation and must vary within every group. This preserves the hierarchical principle and rejects unidentified random-slope specifications before optimization.

[Open the random-slope location–scale guide →](random-slope-location-scale.md)

### Random scale-slope hierarchical location–scale modelling

The Gaussian random scale-slope extension adds **one participant/group-specific numeric slope in the log-scale equation** while retaining the location random intercept. Its latent state is `(location intercept, log-scale intercept, log-scale slope)` with a full positive-definite 3 × 3 covariance matrix and three-dimensional adaptive Gauss–Hermite quadrature.

The scale-slope variable must also enter the fixed log-scale equation and must vary within every group. This makes participant/group differences in residual-variability associations estimable without interpreting them as artifact, sensor-validity or causal effects.

[Open the random scale-slope location–scale guide →](random-scale-slope-location-scale.md)

### Joint random-slope hierarchical location–scale modelling

The joint Gaussian extension adds **one participant/group-specific numeric slope in each equation**. Its latent state is `(location intercept, location slope, log-scale intercept, log-scale slope)` with a full positive-definite 4 × 4 covariance matrix and four-dimensional adaptive Gauss–Hermite quadrature.

Each slope variable must enter the corresponding fixed equation and vary within every group. The location and scale slope variables may be the same observed variable or different variables. The implementation explicitly reports the `q^4` quadrature cost and uses a bounded 3–7 point range.

[Open the joint random-slope location–scale guide →](joint-random-slopes-location-scale.md)

## Validation boundary

The latest fully certified public methods baseline is PR **#121**, merge SHA `67337b0a38a70c9383f478321443f63e42f69234`. Its merge tree is identical to the qualified PR head tree, its GitHub signature is verified/valid, and all **14/14 exact-main push workflow families** completed successfully after merge.

The certified baseline passes **701/701 tests**, **11,836/11,836 statements = 100.00%**, and the frozen export audit remains **406/406 with 0 pending**. Exact-main raw branch coverage is **5,995/6,014 = 99.6841%**. All **19** uncovered branch arcs are explicitly audited structural debt, with **0 unexpected**, **0 stale**, and **0 unaudited** branch debt; audited accounting is **6,014/6,014 = 100.0000%**. The random scale-slope module itself passes **332/332 statements** and **86/86 branches**.

The joint random-slope implementation documented above is a development candidate until its own exact-head qualification and post-merge exact-main certification complete. Pre-merge evidence is never substituted for post-merge evidence.

Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts; development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. None of the location–scale implementations by itself:

- identifies or corrects motion, eye-tracking, or physiological artifacts;
- establishes sensor validity or reliability;
- performs sensor-validity weighting;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The Gaussian random-intercept method covers Gaussian conditional outcomes. The robust extension adds symmetric Student-t conditional outcomes. The location-random-slope extension adds one participant/group-specific numeric slope in the Gaussian location equation and treats it as association heterogeneity, not a causal effect or error-free participant trait. The random scale-slope extension adds one participant/group-specific numeric slope in the Gaussian log-scale equation and treats it as residual-heterogeneity association, not an artifact or sensor-validity score. The joint extension combines one slope in each equation while retaining the same conservative interpretation boundary. Additional random slopes, crossed random effects, skewed heavy-tail families, mixture models, Bayesian priors and causal interpretation remain outside the current location–scale implementation family.
