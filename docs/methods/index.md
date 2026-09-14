# Python-native methods

`gpbiometricspy` preserves a completed **406/406** semantic-parity surface against the frozen `gpbiometrics 2.0.0` R reference. The pages in this section document **additive Python-native methodological extensions** that sit outside that frozen export contract.

Keeping these methods separate is deliberate: new methodological research should be discoverable and publishable without blurring the distinction between R-parity work and later Python-native development.

## Available methods

### Timebase provenance and multimodal alignment certification

The timebase-provenance layer makes timing evidence explicit before multimodal fusion. It distinguishes nominal sampling specifications from timestamp-derived rates, records jitter, gaps, duplicates, backward steps and counter-derived timing, estimates offset or affine relationships between matched clock anchors, and binds the resulting evidence into deterministic SHA-256 certificates.

Certification is deliberately fail-closed: failed timebase audits cannot be certified, warnings require explicit acceptance, clock identities must agree, alignment residuals must satisfy a declared tolerance, and corrected streams must have positive temporal overlap. Clock correction is kept separate from interpolation or resampling, and the method does not interpret small anchor residuals as proof of sub-millisecond hardware synchronization.

[Open the timebase provenance and multimodal alignment guide →](timebase-provenance.md)

### Cardiac variability source provenance

The cardiac-source provenance layer separates ECG-NN HRV, ECG-RR variability, PPG pulse-rate variability, incompletely documented device intervals, vendor-precomputed variability metrics, and sampled heart-rate series before downstream analysis.

Its fail-closed operation contract prevents uncleaned RR from being silently relabelled NN-HRV, prevents PPG-PRV from being treated as globally interchangeable with ECG-HRV, keeps vendor metrics metric-only, and blocks reconstruction of beat-to-beat HRV/PRV from sampled HR. Immutable source declarations are bound to deterministic SHA-256 provenance certificates and can be attached to metric-specific agreement workflows.

[Open the cardiac variability source provenance guide →](cardiac-source-provenance.md)

### Grouped mixed-effects boosting

The grouped mixed-effects boosting method combines deterministic shallow regression-tree boosting with shrinkage-estimated random intercepts for nonlinear prediction of continuous outcomes observed repeatedly within one grouping factor.

It explicitly separates conditional prediction for groups observed during training from marginal prediction for unseen groups, performs whole-group rather than row-wise cross-validation, and uses level-aware permutation importance. The method was exact-main certified through PR **#127** and is additive to, rather than part of, the frozen 406-export R-parity contract.

[Open the grouped mixed-effects boosting guide →](grouped-mixed-boosting.md)

### Grouped ordinal mixed-effects boosting — candidate

The grouped ordinal candidate extends the same deterministic, group-aware philosophy to **ordered outcomes**. It combines a proportional-odds cumulative-logit model with shallow-tree score boosting and shrinkage-estimated group intercepts, requires an explicit scientifically meaningful category order, distinguishes marginal new-group prediction from conditional seen-group prediction, and evaluates new-group generalization with whole-group cross-validation.

Its permutation importance uses ranked probability score and preserves the predictor's level: within-group predictors are shuffled within groups, while group-constant predictors are permuted at the group level. The implementation is an independent boosting analogue; it is **not** OMERF, mixfabOF, a random forest, XGBoost, or a fully integrated CLMM.

This method remains a **development candidate** until its own pinned exact-head qualification, merge-object verification and fresh exact-main certification are complete. It does not alter the certified #127 baseline or the frozen 406-export R-parity contract.

[Open the grouped ordinal mixed-effects boosting guide →](grouped-ordinal-boosting.md)

### Hierarchical location–scale modelling

The Gaussian hierarchical location–scale model jointly estimates a fixed-effects mean equation, a fixed-effects log residual-scale equation, correlated participant/group random intercepts in both equations, two-dimensional adaptive Gauss–Hermite marginal likelihoods, empirical-Bayes summaries for seen groups, explicit population-level prediction semantics for unseen groups, and deterministic diagnostics/certificates.

[Open the Gaussian hierarchical location–scale guide →](hierarchical-location-scale.md)

### Robust Student-t hierarchical location–scale modelling

The robust extension replaces the conditional Gaussian outcome distribution with a symmetric Student-t distribution while retaining the same mean/log-scale structure and correlated participant/group random intercepts. Its degrees of freedom are estimated jointly under a finite-variance constraint.

The implementation distinguishes the Student-t scale parameter from the implied residual standard deviation and treats heavy tails as **distributional robustness**, not evidence that specific observations are artifacts or sensor failures.

[Open the robust Student-t location–scale guide →](robust-hierarchical-location-scale.md)

### Random-slope hierarchical location–scale modelling

The Gaussian random-slope extension adds **one participant/group-specific numeric slope in the location equation** while retaining the log-scale random intercept. Its latent state has a full positive-definite 3 × 3 covariance matrix and three-dimensional adaptive Gauss–Hermite quadrature.

[Open the random-slope location–scale guide →](random-slope-location-scale.md)

### Random scale-slope hierarchical location–scale modelling

The Gaussian random scale-slope extension adds **one participant/group-specific numeric slope in the log-scale equation** while retaining the location random intercept. The scale-slope variable must enter the fixed log-scale equation and vary within every group.

[Open the random scale-slope location–scale guide →](random-scale-slope-location-scale.md)

### Joint random-slope hierarchical location–scale modelling

The joint Gaussian extension adds **one participant/group-specific numeric slope in each equation**. Its latent state uses a full positive-definite 4 × 4 covariance matrix with four-dimensional adaptive Gauss–Hermite quadrature.

[Open the joint random-slope location–scale guide →](joint-random-slopes-location-scale.md)

### Crossed participant–item hierarchical location–scale modelling

The crossed Gaussian extension adds **participant and item/stimulus random intercepts in both the location and log-scale equations**. It uses a joint Laplace approximation over the crossed latent field with analytic gradient/Hessian, incidence-connectivity and replication guards, a dense-latent complexity ceiling, population-versus-conditional prediction semantics, and deterministic certificates.

The method was exact-main certified through PR **#124** and remains part of the current certified development baseline.

[Open the crossed participant–item location–scale guide →](crossed-location-scale.md)

## Validation boundary

The latest fully certified development baseline is PR **#127**, exact-main SHA `e8721b945954f75c98d1d6e5f5b57ce4db9a77dc`, tree `f30bce832732bb9cf73096cea8be826076f75ff1`. The merge tree is exactly equal to the qualified candidate tree at exact PR head `37aa98c4d602bc74fe99ea80b48d78fb4191dad1`. GitHub produced a **two-parent signed merge commit** with parents certified `ad70f7ec87ae11237049c635dde098e077c2c925` and qualified head `37aa98c4d602bc74fe99ea80b48d78fb4191dad1`; that actual topology is recorded explicitly, and the GitHub signature is verified/valid. There was no merge-tree drift.

Both the final candidate and the fresh exact-main generation completed **14/14 workflow families successfully**. The exact-main negative-state audit closed at **0 failures, 0 cancellations, 0 queued and 0 in-progress runs**. The certified baseline passes **766/766 tests**, **13,580/13,580 statements = 100.00%**, and the frozen export audit remains **406/406 with 0 pending**. Exact-main raw branch coverage is **6,609/6,628 = 99.7133%**. All **19** uncovered branch arcs remain explicitly audited structural debt, with **0 unexpected**, **0 stale**, and **0 unaudited** branch debt; audited accounting is **6,628/6,628 = 100.0000%**.

The grouped mixed-effects boosting module passes **357/357 statements and 128/128 branches**. The crossed participant–item module passes **444/444 statements and 168/168 branches**. The timebase-provenance module passes **377/377 statements and 150/150 branches**. The cardiac-source provenance module passes **195/195 statements and 78/78 branches**. Exact-main branch evidence is archived as artifact **10337621839**, SHA-256 `58ae977e911eba725ccb0d0d3173b46c952c73f14c5ca309216a392cc37a7383`.

This certification uses fresh post-merge evidence from the exact merge SHA. Pre-merge qualification was not substituted for exact-main evidence. Docs strict-build and main-branch Pages deployment, CodeQL, interoperability, Deep Parity, private real-data validation, and all triggered Studio release/packaging/signing/installer/readiness families were terminal green.

The grouped ordinal mixed-effects boosting method documented above is a **candidate beyond this boundary**. Its local focused development checks do not promote it into the certified baseline; fresh immutable-candidate GitHub evidence is required.

Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts: **641 tests**, **10,456/10,456 statements = 100.00%**, and **5,629/5,648 raw branches = 99.6636%**. Development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. None of the location–scale implementations by itself identifies or corrects artifacts, establishes sensor validity/reliability, performs sensor-validity weighting, identifies causal effects, or infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The timebase-provenance layer characterizes and binds recorded timing evidence; it does not prove hardware synchronization beyond supplied anchors or establish sensor validity. The cardiac-source provenance layer characterizes cardiac-input identity; it does not convert PPG-PRV into ECG-HRV or recreate unobserved beat intervals from sampled HR.

The grouped mixed-effects boosting method is a nonlinear predictive model. Its random intercepts account for one grouping factor in prediction; feature importance is predictive rather than causal; conditional performance applies to observed groups; and population/new-group generalization requires group-held-out evaluation. It does not provide likelihood-based p-values, confidence intervals, crossed random effects, or random slopes.

The grouped ordinal candidate is likewise predictive. Its cumulative-logit thresholds encode ordered outcome structure, while its fitted group offsets are shrinkage estimates rather than stable participant traits. It is not a full integrated-likelihood cumulative-link mixed model and does not inherit inferential claims from OMERF, mixfabOF, random forests, or generalized boosting frameworks.

The Gaussian random-intercept location–scale method covers Gaussian conditional outcomes; the robust extension adds symmetric Student-t conditional outcomes; the slope extensions model association heterogeneity; and the crossed model adds participant and item/stimulus random intercepts. Crossed random slopes, further random-slope structures, skewed heavy-tail families, mixture models, Bayesian priors and causal interpretation remain outside the current location–scale implementation family.
