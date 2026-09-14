# Python-native methods

`gpbiometricspy` preserves a completed **406/406** semantic-parity surface against the frozen `gpbiometrics 2.0.0` R reference. The pages in this section document **additive Python-native methodological extensions** that sit outside that frozen export contract.

Keeping these methods separate is deliberate: new methodological research should be discoverable and publishable without blurring the distinction between R-parity work and later Python-native development.

## Available methods

### Timebase provenance and multimodal alignment certification

The timebase-provenance layer makes timing evidence explicit before multimodal fusion. It distinguishes nominal sampling specifications from timestamp-derived rates, records jitter, gaps, duplicates, backward steps and counter-derived timing, estimates offset or affine relationships between matched clock anchors, and binds the resulting evidence into deterministic SHA-256 certificates.

Certification is deliberately fail-closed: failed timebase audits cannot be certified, warnings require explicit acceptance, clock identities must agree, alignment residuals must satisfy a declared tolerance, and corrected streams must have positive temporal overlap. Clock correction is kept separate from interpolation or resampling, and the method does not interpret small anchor residuals as proof of sub-millisecond hardware synchronization.

[Open the timebase provenance and multimodal alignment guide →](timebase-provenance.md)

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

### Crossed participant–item hierarchical location–scale modelling

The crossed Gaussian extension adds **participant and item/stimulus random intercepts in both the location and log-scale equations**. Participant effects and item effects each use their own correlated 2 × 2 covariance matrix, allowing both clustering factors to contribute location heterogeneity and residual-scale heterogeneity.

Because crossed participant and item effects cannot be integrated independently group by group, the implementation uses a **joint Laplace approximation** over the complete crossed latent field with an analytic gradient/Hessian, explicit incidence-connectivity and replication guards, a dense-latent complexity ceiling, population-versus-conditional prediction semantics for unseen participants/items, and deterministic reproducibility certificates.

The method was exact-main certified through PR **#124** and remains part of the current PR #125 certified development baseline. It is additive to, and does not modify, the frozen 406-export R-parity contract.

[Open the crossed participant–item location–scale guide →](crossed-location-scale.md)

## Validation boundary

The latest fully certified development baseline is PR **#125**, merge SHA `1464e46cd75373eb634c3df12dedd5e7764af395`, tree `2b4d4f532a2414179fe916fcae208ba20e063461`. The merge tree is identical to the qualified candidate tree at exact PR head `aafeab90e9b863746f60cd018accb1d336cc8a5d`, and its GitHub signature is verified/valid. PR #125 is a **two-parent merge commit**, with parents `eb8c737f93e952f7bec0e6d7958336f1ecf469f5` and `aafeab90e9b863746f60cd018accb1d336cc8a5d`; that topology is recorded explicitly rather than described as a squash. There was no merge-tree drift.

Both the candidate and exact-main generations completed **14/14 workflow families successfully**. The fresh exact-main generation had **0 failures, 0 cancellations, 0 queued and 0 in-progress runs** at certification. The certified baseline passes **733/733 tests**, **13,028/13,028 statements = 100.00%**, and the frozen export audit remains **406/406 with 0 pending**. Exact-main raw branch coverage is **6,403/6,422 = 99.7041%**. All **19** uncovered branch arcs remain explicitly audited structural debt, with **0 unexpected**, **0 stale**, and **0 unaudited** branch debt; audited accounting is **6,422/6,422 = 100.0000%**.

The crossed participant–item module passes **444/444 statements and 168/168 branches**. The timebase-provenance module passes **377/377 statements and 150/150 branches**. Exact-main branch evidence is archived as artifact **10328745378**, SHA-256 `c0e767e4a9c6cad4ed87a3368e29ee778bf32a89e1809e1515c6581b29949108`. PR **#124**, merge SHA `eb8c737f93e952f7bec0e6d7958336f1ecf469f5`, is the certified predecessor that introduced the crossed participant–item model.

This certification uses fresh post-merge evidence from the exact merge SHA. Pre-merge qualification was not substituted for exact-main evidence. Docs strict-build and main-branch Pages deployment, CodeQL, interoperability, Deep Parity, private real-data validation, and all triggered Studio packaging/installer/readiness families were terminal green.

Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts: **641 tests**, **10,456/10,456 statements = 100.00%**, and **5,629/5,648 raw branches = 99.6636%**. Development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. None of the location–scale implementations by itself:

- identifies or corrects motion, eye-tracking, or physiological artifacts;
- establishes sensor validity or reliability;
- performs sensor-validity weighting;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The timebase-provenance layer likewise characterizes and binds recorded timing evidence; it does not establish sensor validity, reconstruct unsampled physiological information, prove hardware synchronization beyond the supplied anchors, or justify causal ordering beyond the temporal accuracy supported by the acquisition design.

The Gaussian random-intercept method covers Gaussian conditional outcomes. The robust extension adds symmetric Student-t conditional outcomes. The location-random-slope extension adds one participant/group-specific numeric slope in the Gaussian location equation and treats it as association heterogeneity, not a causal effect or error-free participant trait. The random scale-slope extension adds one participant/group-specific numeric slope in the Gaussian log-scale equation and treats it as residual-heterogeneity association, not an artifact or sensor-validity score. The joint extension combines one slope in each equation while retaining the same conservative interpretation boundary. The crossed model adds participant and item/stimulus random intercepts in both equations while retaining the same conservative interpretation boundary. Crossed random slopes, further random-slope structures, skewed heavy-tail families, mixture models, Bayesian priors and causal interpretation remain outside the current location–scale implementation family.