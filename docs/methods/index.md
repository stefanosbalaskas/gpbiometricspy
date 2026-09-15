# Python-native methods

`gpbiometricspy` preserves a completed **406/406** semantic-parity surface against the frozen `gpbiometrics 2.0.0` R reference. The pages in this section document **additive Python-native methodological extensions** that sit outside that frozen export contract.

Keeping these methods separate is deliberate: new methodological research should be discoverable and publishable without blurring the distinction between R-parity work and later Python-native development.

## Available methods

### Timebase provenance and multimodal alignment certification

The timebase-provenance layer separates nominal acquisition settings from timing characteristics observed in recorded timestamps. It audits jitter, gaps, duplicates, backward steps and counter-derived timing; estimates offset or affine clock mappings from matched anchors; and binds the evidence into deterministic SHA-256 certificates.

[Open the timebase provenance and multimodal alignment guide →](timebase-provenance.md)

### Cardiac variability source provenance

The cardiac-source provenance layer separates ECG-NN HRV, ECG-RR variability, PPG pulse-rate variability, incompletely documented device intervals, vendor-precomputed variability metrics, and sampled heart-rate series before downstream analysis.

[Open the cardiac variability source provenance guide →](cardiac-source-provenance.md)

### Grouped mixed-effects boosting

The grouped mixed-effects boosting method combines deterministic shallow regression-tree boosting with shrinkage-estimated random intercepts for nonlinear prediction of continuous repeated outcomes. It separates seen-group conditional prediction from unseen-group population prediction and uses whole-group validation.

[Open the grouped mixed-effects boosting guide →](grouped-mixed-boosting.md)

### Grouped ordinal mixed-effects boosting

The grouped ordinal method targets explicitly ordered categorical outcomes. It combines proportional-odds cumulative logits, ordered thresholds, deterministic shallow-tree score boosting and shrinkage-estimated group random intercepts while retaining group-aware evaluation and explicit seen/unseen prediction semantics.

[Open the grouped ordinal mixed-effects boosting guide →](grouped-ordinal-boosting.md)

### Hierarchical location–scale modelling

The Gaussian hierarchical location–scale model jointly estimates a fixed-effects mean equation, a fixed-effects log residual-scale equation, correlated participant/group random intercepts in both equations, adaptive Gauss–Hermite marginal likelihoods, empirical-Bayes summaries and explicit population-level prediction for unseen groups.

[Open the Gaussian hierarchical location–scale guide →](hierarchical-location-scale.md)

### Robust Student-t hierarchical location–scale modelling

The robust extension replaces the conditional Gaussian outcome distribution with a symmetric Student-t distribution while retaining the same mean/log-scale structure and correlated participant/group random intercepts. Heavy tails are treated as **distributional robustness**, not evidence that specific observations are artifacts or sensor failures.

[Open the robust Student-t location–scale guide →](robust-hierarchical-location-scale.md)

### Random-slope hierarchical location–scale modelling

The Gaussian random-slope extension adds one participant/group-specific numeric slope in the **location equation** while retaining the log-scale random intercept. The latent state is `(location intercept, location slope, log-scale intercept)` with a full positive-definite 3 × 3 covariance matrix.

[Open the random-slope location–scale guide →](random-slope-location-scale.md)

### Random scale-slope hierarchical location–scale modelling

The Gaussian random scale-slope extension adds one participant/group-specific numeric slope in the **log-scale equation** while retaining the location random intercept. The latent state is `(location intercept, log-scale intercept, log-scale slope)` with a full positive-definite 3 × 3 covariance matrix.

[Open the random scale-slope location–scale guide →](random-scale-slope-location-scale.md)

### Joint random-slope hierarchical location–scale modelling

The joint Gaussian extension adds one participant/group-specific numeric slope in **each equation**. Its latent state is `(location intercept, location slope, log-scale intercept, log-scale slope)` with a full positive-definite 4 × 4 covariance matrix and bounded four-dimensional adaptive quadrature.

[Open the joint random-slope location–scale guide →](joint-random-slopes-location-scale.md)

### Crossed participant–item hierarchical location–scale modelling

The crossed Gaussian extension adds participant and item/stimulus random intercepts in both the location and log-scale equations. Participant effects and item effects each use their own correlated 2 × 2 covariance matrix. Because the crossed latent families cannot be integrated independently, the implementation uses a joint Laplace approximation over the complete latent field.

[Open the crossed participant–item location–scale guide →](crossed-location-scale.md)

### Crossed participant–item random-slope location–scale modelling

The crossed random-slope extension adds one **location random slope for each crossed factor**. Each participant and item/stimulus has a trivariate block `(location intercept, location slope, log-scale intercept)` with its own positive-definite 3 × 3 covariance matrix. The complete latent field has dimension `3(P + I)`.

PR **#129** is exact-main certified at merge SHA `d078e0366ace49c3ebeb2f6800bad6394d70631e`.

[Open the crossed participant–item random-slope guide →](crossed-random-slopes-location-scale.md)

### Crossed participant–item random scale-slope location–scale modelling

The crossed random scale-slope method adds one **log-scale random slope for each crossed factor**. Each participant and item/stimulus receives a trivariate block `(location intercept, log-scale intercept, log-scale slope)` with its own positive-definite 3 × 3 covariance matrix. The complete latent field has dimension `3(P + I)`.

PR **#133** introduced the method; PR **#134** added a test-only deterministic regression for a private loop-exhaustion branch. The final exact-main scientific state is formally certified at `33175e1d0507109c2af1f526b460f0f3ba6a7063`.

[Open the crossed participant–item random scale-slope guide →](crossed-random-scale-slopes-location-scale.md)

### Crossed participant–item joint random-slope location–scale modelling

The active development tranche adds **both a location random slope and a log-scale random slope for each crossed factor**. Each participant and each item/stimulus receives a four-dimensional block `(location intercept, location slope, log-scale intercept, log-scale slope)` with its own unrestricted positive-definite 4 × 4 covariance matrix. The complete latent field has dimension `4(P + I)` and is handled with the established joint dense-Laplace strategy.

Every location-slope predictor must enter `mean_cols`; every scale-slope predictor must enter `scale_cols`; and every declared slope must vary within every corresponding crossed-factor level. The implementation requires at least eight participant and eight item levels and retains explicit conditional/population prediction for unseen levels.

This method is **not yet a certified baseline**. Its development page records the exact scope and interpretation boundary while CI qualification is in progress.

[Open the crossed participant–item joint random-slope guide →](crossed-joint-random-slopes-location-scale.md)

## Validation boundary

The latest fully certified scientific development baseline remains PR **#134**, exact-main SHA `33175e1d0507109c2af1f526b460f0f3ba6a7063`, tree `37a038b74c8e4cf5a547105b027f588cbc307440`. Its sole parent is PR #133 merge SHA `f4ee2c7ac73c062c53682cf8be67f40b8768c63a`, the GitHub signature is verified/valid, and formal certification checkpoint comment **5676677748** records the exact-main state.

That certified scientific baseline passes **824/824 tests**, **14,757/14,757 statements**, and the frozen export audit remains **406/406 with 0 pending**. Tests #626 is **12/12 platform/Python lanes green**. Raw branch coverage is **7,025/7,044 = 99.7303%**. All **19** uncovered branch arcs are explicitly audited structural/caller-dominated debt, with **0 unexpected**, **0 stale**, and **0 unaudited** entries.

Exact-main branch evidence is Branch Coverage #406, run **34941909652**, artifact **10385841209**, SHA-256 `621c8d8c724323426af32c7d7bb5f3631a0b5a7188422b99e7647ed8036a84d4`.

A later documentation-only descendant, `0b7084352362d297dc05f127d4bcbc924cd24873`, updates the public method documentation and Pages site without changing production code, tests, workflow definitions, package metadata, or the structural branch-debt ledger. Its docs-only completion checkpoint is PR #135 comment **5676925906**.

Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts. Development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

These pages document statistical and computational methods, not automatic scientific interpretation. None of the location–scale implementations by itself:

- identifies or corrects motion, eye-tracking, or physiological artifacts;
- establishes sensor validity or reliability;
- performs sensor-validity weighting;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The timebase-provenance layer characterizes and binds recorded timing evidence; it does not establish sensor validity, reconstruct unsampled physiological information, prove hardware synchronization beyond supplied anchors, or justify causal ordering beyond the temporal accuracy supported by the acquisition design.

The cardiac-source provenance layer characterizes and binds the scientific identity of cardiac inputs; it does not prove manufacturer claims, infer undocumented beat-processing algorithms, convert PPG-PRV into ECG-HRV, or recreate unobserved beat intervals from sampled HR.

The grouped boosting methods are predictive rather than causal. Their random intercepts, thresholds, ranked losses and permutation importances are predictive constructs rather than latent-trait or inferential tests.

The Gaussian, robust Student-t, random-slope, scale-slope, joint-slope, crossed, crossed-random-slope, crossed-random-scale-slope and crossed-joint-slope location–scale models estimate conditional distributional or association heterogeneity under their stated specifications. Random slopes are not causal effects or error-free traits; log-scale effects are not artifact, reliability or sensor-validity scores.