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

It explicitly separates conditional prediction for groups observed during training from marginal prediction for unseen groups, performs whole-group rather than row-wise cross-validation, and uses level-aware permutation importance: within-group predictors are shuffled within groups, while group-constant predictors are permuted at the group level. The implementation is a narrow dependency-free research analogue, not an implementation of XGBoost and not a causal-inference method.

[Open the grouped mixed-effects boosting guide →](grouped-mixed-boosting.md)

### Hierarchical location–scale modelling

The Gaussian hierarchical location–scale model jointly estimates a fixed-effects mean equation, a fixed-effects log residual-scale equation, correlated participant/group random intercepts in both equations, adaptive Gauss–Hermite group marginal likelihoods, empirical-Bayes summaries for seen groups, explicit population-level prediction semantics for unseen groups, and deterministic reproducibility certificates.

[Open the Gaussian hierarchical location–scale guide →](hierarchical-location-scale.md)

### Robust Student-t hierarchical location–scale modelling

The robust extension replaces the conditional Gaussian outcome distribution with a symmetric Student-t distribution while retaining the same mean/log-scale structure and correlated participant/group random intercepts. Its degrees of freedom are estimated jointly under a finite-variance constraint. Heavy tails are treated as **distributional robustness**, not evidence that specific observations are artifacts or sensor failures.

[Open the robust Student-t location–scale guide →](robust-hierarchical-location-scale.md)

### Random-slope hierarchical location–scale modelling

The Gaussian random-slope extension adds **one participant/group-specific numeric slope in the location equation** while retaining the log-scale random intercept. The latent state is `(location intercept, location slope, log-scale intercept)` with a full positive-definite 3 × 3 covariance matrix and three-dimensional adaptive Gauss–Hermite quadrature.

The random-slope variable must also enter the fixed mean equation and must vary within every group.

[Open the random-slope location–scale guide →](random-slope-location-scale.md)

### Random scale-slope hierarchical location–scale modelling

The Gaussian random scale-slope extension adds **one participant/group-specific numeric slope in the log-scale equation** while retaining the location random intercept. Its latent state is `(location intercept, log-scale intercept, log-scale slope)` with a full positive-definite 3 × 3 covariance matrix and three-dimensional adaptive Gauss–Hermite quadrature.

The scale-slope variable must also enter the fixed log-scale equation and must vary within every group. It is residual-heterogeneity association, not an artifact, reliability or sensor-validity score.

[Open the random scale-slope location–scale guide →](random-scale-slope-location-scale.md)

### Joint random-slope hierarchical location–scale modelling

The joint Gaussian extension adds **one participant/group-specific numeric slope in each equation**. Its latent state is `(location intercept, location slope, log-scale intercept, log-scale slope)` with a full positive-definite 4 × 4 covariance matrix and four-dimensional adaptive Gauss–Hermite quadrature.

Each slope variable must enter the corresponding fixed equation and vary within every group. The location and scale slope variables may be the same observed variable or different variables.

[Open the joint random-slope location–scale guide →](joint-random-slopes-location-scale.md)

### Crossed participant–item hierarchical location–scale modelling

The crossed Gaussian extension adds **participant and item/stimulus random intercepts in both the location and log-scale equations**. Participant effects and item effects each use their own correlated 2 × 2 covariance matrix, allowing both clustering factors to contribute location heterogeneity and residual-scale heterogeneity.

Because crossed participant and item effects cannot be integrated independently group by group, the implementation uses a **joint Laplace approximation** over the complete crossed latent field with analytic latent derivatives, incidence-connectivity and replication guards, a dense-latent complexity ceiling, population-versus-conditional prediction semantics for unseen participants/items, and deterministic reproducibility certificates.

[Open the crossed participant–item location–scale guide →](crossed-location-scale.md)

### Crossed participant–item random-slope location–scale modelling

The development candidate extends the crossed Gaussian model with **one location random slope for each crossed factor**. Each participant and each item/stimulus has a trivariate random-effects block `(location intercept, location slope, log-scale intercept)` with its own unrestricted positive-definite 3 × 3 covariance matrix. The complete latent field has dimension `3(P + I)` and is integrated with the same joint dense-Laplace strategy.

Each random-slope predictor must also enter the fixed mean equation and must vary within every level of the corresponding crossed factor. The method retains explicit population semantics for unseen participants/items and deterministic certificates. It deliberately does not add log-scale random slopes, participant × item interaction effects, a general random-effects grammar, mixture distributions, Bayesian priors, or causal interpretation.

This method remains a **PR #129 development candidate** until fresh exact-head qualification, merge verification and exact-main certification are complete.

[Open the crossed participant–item random-slope guide →](crossed-random-slopes-location-scale.md)

## Validation boundary

The latest fully certified development baseline is PR **#127**, exact-main SHA `e8721b945954f75c98d1d6e5f5b57ce4db9a77dc`, tree `f30bce832732bb9cf73096cea8be826076f75ff1`. The GitHub merge signature is verified/valid and the merge tree is identical to the exact qualified candidate tree, so there was no content drift.

PR #127 completed **14/14 exact-head workflow families** before merge and **14/14 fresh exact-main push workflow families** after merge, with no evidence waiver or stale-run substitution. The certified exact-main baseline passes **766/766 tests**, **13,580/13,580 statements**, and the frozen export audit remains **406/406 with 0 pending**. Raw branch coverage is **6,609/6,628 = 99.7133%**. All **19** uncovered branch arcs are explicitly audited structural/caller-dominated debt, with **0 unexpected**, **0 stale**, and **0 unaudited** entries; audited structural accounting is **6,628/6,628 = 100.0000%** without redefining raw branch coverage as 100%.

The grouped mixed-effects boosting module passes **357/357 statements and 128/128 branches**. The crossed participant–item module passes **444/444 statements and 168/168 branches**. The timebase-provenance module passes **377/377 statements and 150/150 branches**. The cardiac-source provenance module passes **195/195 statements and 78/78 branches**. Exact-main branch evidence is archived as artifact **10337621839**, SHA-256 `58ae977e911eba725ccb0d0d3173b46c952c73f14c5ca309216a392cc37a7383`.

PR #129 diagnostic evidence is intentionally not represented as certification. Its hardened diagnostic generation demonstrated **779/779 tests**, **14,015/14,015 statements**, **435/435 statements and 148/148 branches** in the new crossed-random-slope module, and raw branch coverage **6,757/6,776 = 99.7196%**, with the same 19 audited arcs and 0 unexpected/stale/unaudited debt. That diagnostic run failed the structural-debt workflow solely because the denominator was still frozen at the PR #127 value; fresh normalized exact-head CI remains authoritative before any merge.

Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts: **641 tests**, **10,456/10,456 statements = 100.00%**, and **5,629/5,648 raw branches = 99.6636%**. Development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. None of the location–scale implementations by itself:

- identifies or corrects motion, eye-tracking, or physiological artifacts;
- establishes sensor validity or reliability;
- performs sensor-validity weighting;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The timebase-provenance layer characterizes and binds recorded timing evidence; it does not establish sensor validity, reconstruct unsampled physiological information, prove hardware synchronization beyond supplied anchors, or justify causal ordering beyond the temporal accuracy supported by the acquisition design.

The cardiac-source provenance layer characterizes and binds the scientific identity of cardiac inputs; it does not prove manufacturer claims, infer undocumented beat-processing algorithms, convert PPG-PRV into ECG-HRV, or recreate unobserved beat intervals from sampled HR.

The grouped mixed-effects boosting method is a nonlinear predictive model. Its feature importance is predictive rather than causal; conditional performance applies to observed groups; and population/new-group generalization requires group-held-out evaluation. It does not provide likelihood-based p-values, confidence intervals, crossed random effects, or random slopes.

The Gaussian, robust Student-t, random-slope, scale-slope, joint-slope, crossed and crossed-random-slope location–scale models estimate conditional distributional or association heterogeneity under their stated specifications. Random slopes are not causal effects or error-free traits; log-scale effects are not artifact or sensor-validity scores. Crossed log-scale random slopes, richer crossed random-effect structures, skewed heavy-tail families, mixtures, Bayesian priors and causal interpretation remain outside the current implementation family.
