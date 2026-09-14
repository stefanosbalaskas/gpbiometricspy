# Python-native methods

`gpbiometricspy` preserves a completed **406/406** semantic-parity surface against the frozen `gpbiometrics 2.0.0` R reference. The pages in this section document **additive Python-native methodological extensions** outside that frozen export contract.

Keeping these methods separate is deliberate: methodological research can advance without blurring the distinction between R-parity work and later Python-native development.

## Available methods

### Timebase provenance and multimodal alignment certification

The timebase-provenance layer makes timing evidence explicit before multimodal fusion. It distinguishes nominal sampling specifications from timestamp-derived rates, records jitter, gaps, duplicates, backward steps and counter-derived timing, estimates offset or affine relationships between matched clock anchors, and binds the evidence into deterministic SHA-256 certificates.

[Open the timebase provenance and multimodal alignment guide →](timebase-provenance.md)

### Cardiac variability source provenance

The cardiac-source provenance layer separates ECG-NN HRV, ECG-RR variability, PPG pulse-rate variability, incompletely documented device intervals, vendor-precomputed variability metrics, and sampled heart-rate series before downstream analysis. Its fail-closed operation contract prevents source identities from being silently relabelled or reconstructed beyond the recorded evidence.

[Open the cardiac variability source provenance guide →](cardiac-source-provenance.md)

### Grouped mixed-effects boosting

The grouped mixed-effects boosting method combines deterministic shallow regression-tree boosting with shrinkage-estimated random intercepts for nonlinear prediction of continuous outcomes observed repeatedly within one grouping factor. It separates conditional prediction for seen groups from marginal prediction for unseen groups, uses whole-group cross-validation, and applies level-aware permutation importance.

[Open the grouped mixed-effects boosting guide →](grouped-mixed-boosting.md)

### Grouped ordinal mixed-effects boosting — candidate

The grouped ordinal candidate extends the same deterministic, group-aware design to **ordered outcomes**. It combines proportional-odds cumulative logits, shallow-tree score boosting and shrinkage-estimated group intercepts; requires an explicit scientifically meaningful category order; distinguishes marginal new-group prediction from conditional seen-group prediction; and evaluates new-group generalization with whole-group cross-validation.

Its permutation importance uses ranked probability score and preserves predictor level: within-group predictors are shuffled within groups, while group-constant predictors are permuted at the group level. The implementation is an independent boosting analogue; it is **not** OMERF, mixfabOF, a random forest, XGBoost, or a fully integrated CLMM.

This method remains a **PR #130 development candidate** until its own pinned exact-head qualification, merge-object verification and fresh exact-main certification are complete.

[Open the grouped ordinal mixed-effects boosting guide →](grouped-ordinal-boosting.md)

### Hierarchical location–scale modelling

The Gaussian hierarchical location–scale model jointly estimates a fixed-effects mean equation, a fixed-effects log residual-scale equation, correlated participant/group random intercepts in both equations, adaptive Gauss–Hermite marginal likelihoods, empirical-Bayes summaries for seen groups, explicit population-level prediction semantics for unseen groups, and deterministic diagnostics/certificates.

[Open the Gaussian hierarchical location–scale guide →](hierarchical-location-scale.md)

### Robust Student-t hierarchical location–scale modelling

The robust extension replaces the conditional Gaussian outcome distribution with a symmetric Student-t distribution while retaining the same mean/log-scale structure and correlated participant/group random intercepts. Heavy tails are treated as **distributional robustness**, not evidence that observations are artifacts or sensor failures.

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

The crossed Gaussian extension adds **participant and item/stimulus random intercepts in both the location and log-scale equations**. It uses a joint Laplace approximation over the crossed latent field with analytic latent derivatives, incidence-connectivity and replication guards, a dense-latent complexity ceiling, population-versus-conditional prediction semantics, and deterministic certificates.

[Open the crossed participant–item location–scale guide →](crossed-location-scale.md)

### Crossed participant–item random-slope location–scale modelling

The certified crossed Gaussian random-slope extension adds **one location random slope for each crossed factor**. Each participant and each item/stimulus has a trivariate random-effects block `(location intercept, location slope, log-scale intercept)` with its own unrestricted positive-definite 3 × 3 covariance matrix. The complete latent field has dimension `3(P + I)` and is integrated with the joint dense-Laplace strategy.

Each random-slope predictor must also enter the fixed mean equation and vary within every level of the corresponding crossed factor. The method retains explicit population semantics for unseen participants/items and deterministic certificates. It deliberately does not add log-scale random slopes, participant × item interaction effects, a general random-effects grammar, mixture distributions, Bayesian priors, or causal interpretation.

[Open the crossed participant–item random-slope guide →](crossed-random-slopes-location-scale.md)

## Validation boundary

The latest fully certified development baseline is PR **#129**, exact-main SHA `d078e0366ace49c3ebeb2f6800bad6394d70631e`, tree `50fc42f90cd53aafa81bf277da6f82045a3cd75d`. Its parents are certified PR #127 `e8721b945954f75c98d1d6e5f5b57ce4db9a77dc` and exact qualified PR #129 head `5c35f1d4…`; GitHub's signature is verified/valid and the merge tree matches the qualified candidate tree.

PR #129 completed **14/14 exact-head workflow families** before merge and **14/14 fresh exact-main push workflow families** after merge, with no evidence waiver or stale-run substitution. The certified exact-main baseline passes **782/782 tests**, **14,015/14,015 statements**, and the frozen export audit remains **406/406 with 0 pending**. Raw branch coverage is **6,757/6,776 = 99.7196%**. All **19** uncovered branch arcs are explicitly audited structural/caller-dominated debt, with **0 unexpected**, **0 stale**, and **0 unaudited** entries; audited structural accounting is **6,776/6,776 = 100.0000%** without redefining raw branch coverage as 100%.

The crossed participant–item random-slope module passes **435/435 statements and 148/148 branches**. The grouped mixed-effects boosting module passes **357/357 statements and 128/128 branches**. Exact-main branch evidence is archived as artifact **10344881054**, SHA-256 `3db0de45be9371c32673a37c510b6997b0cbce017dba06e751589d31a8ce7ee2`.

The grouped ordinal method documented above is a **candidate beyond this boundary**. Pre-PR focused evidence of **17/17 tests, 387/387 statements and 138/138 branches** is development evidence only; fresh immutable-candidate GitHub Actions remains authoritative for qualification. If reproduced on the certified #129 base, the expected raw branch accounting is **6,895/6,914 = 99.7252%** with the same 19 audited arcs.

Stable `0.1.6` remains a distinct frozen release with its own release evidence and artifacts: **641 tests**, **10,456/10,456 statements = 100.00%**, and **5,629/5,648 raw branches = 99.6636%**. Development-line method work does not retroactively alter the stable-release record.

## Scientific guardrails

The methods section documents statistical and computational methods, not automatic scientific interpretation. None of the methods by itself identifies or corrects eye-tracking or physiological artifacts, establishes sensor validity or reliability, performs sensor-validity weighting, identifies causal effects, or infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from physiological or eye-tracking measurements.

The timebase-provenance layer characterizes and binds recorded timing evidence; it does not prove hardware synchronization beyond supplied anchors or establish sensor validity. The cardiac-source provenance layer characterizes cardiac-input identity; it does not convert PPG-PRV into ECG-HRV or recreate unobserved beat intervals from sampled HR.

Grouped mixed-effects boosting and grouped ordinal boosting are predictive methods. Their feature importance is predictive rather than causal; conditional performance applies to observed groups; and population/new-group generalization requires group-held-out evaluation. The ordinal method's cumulative-logit thresholds encode ordered outcome structure, while fitted group offsets are shrinkage estimates rather than stable participant traits. It is not a fully integrated-likelihood cumulative-link mixed model.

The Gaussian, robust Student-t, random-slope, scale-slope, joint-slope, crossed and crossed-random-slope location–scale models estimate conditional distributional or association heterogeneity under their stated specifications. Random slopes are not causal effects or error-free traits; log-scale effects are not artifact or sensor-validity scores. Crossed log-scale random slopes, richer crossed random-effect structures, skewed heavy-tail families, mixtures, Bayesian priors and causal interpretation remain outside the current implementation family.
