# Python-native methods

<div class="gp-page-intro">
The methods here are **additive Python-native extensions**. They do not alter the completed **406/406** semantic-parity surface against frozen `gpbiometrics 2.0.0`. Start from the scientific structure you need to represent, not from the richest available model.
</div>

<div class="gp-chip-row">
<span class="gp-chip">406 / 406 frozen exports</span>
<span class="gp-chip">predictive + distributional families</span>
<span class="gp-chip">one-factor + crossed random structures</span>
<span class="gp-chip">provenance certificates</span>
</div>

## Choose by scientific need

| Scientific need | Start with | Escalate when |
|---|---|---|
| Audit recorded clocks or align streams | [Timebase provenance](timebase-provenance.md) | drift/anchors need an explicit mapping and certificate |
| Establish cardiac input identity | [Cardiac source provenance](cardiac-source-provenance.md) | HRV/PRV interpretation depends on ECG, PPG, device intervals or sampled HR |
| Predict a continuous repeated outcome | [Grouped mixed-effects boosting](grouped-mixed-boosting.md) | nonlinear predictive structure and unseen-group validation matter |
| Predict an ordered repeated outcome | [Grouped ordinal boosting](grouped-ordinal-boosting.md) | the response has meaningful ordered categories |
| Model one-factor mean + residual-scale heterogeneity | [Hierarchical location–scale](hierarchical-location-scale.md) | Gaussian conditional structure is defensible |
| Retain that structure with heavier tails | [Robust Student-t location–scale](robust-hierarchical-location-scale.md) | heavy conditional tails are plausible |
| Let a mean association vary by group | [Location random slope](random-slope-location-scale.md) | a fixed association is too restrictive |
| Let a dispersion association vary by group | [Scale random slope](random-scale-slope-location-scale.md) | log-scale heterogeneity has a supported contrast |
| Let both associations vary by group | [Joint random slopes](joint-random-slopes-location-scale.md) | both random slopes are scientifically required |
| Model participant + item intercept heterogeneity | [Crossed intercepts](crossed-location-scale.md) | both crossed factors contribute clustering |
| Add participant + item mean slopes | [Crossed location slopes](crossed-random-slopes-location-scale.md) | both factors require location-slope variation |
| Add participant + item scale slopes | [Crossed scale slopes](crossed-random-scale-slopes-location-scale.md) | both factors require log-scale-slope variation |
| Add both crossed mean + scale slopes | [Crossed joint slopes](crossed-joint-random-slopes-location-scale.md) | the richest crossed structure is explicitly justified |

<div class="gp-decision">
<strong>Escalation rule:</strong> richer random structures are not automatically better. Every added slope/covariance needs a scientific contrast, within-level variation, enough groups/items, computational support, and an interpretation conditional on the fitted model and acquisition design.
</div>

## Method families

### Provenance before modelling

**[Timebase provenance and multimodal alignment →](timebase-provenance.md)** audits observed timing, jitter, gaps, duplicates and clock mappings, then binds the evidence into deterministic certificates.

**[Cardiac variability source provenance →](cardiac-source-provenance.md)** separates ECG-NN/RR, PPG pulse intervals, device-derived intervals, vendor metrics and sampled heart-rate series before variability analysis.

### Grouped predictive models

**[Grouped mixed-effects boosting →](grouped-mixed-boosting.md)** combines shallow-tree boosting with shrinkage-estimated group random intercepts for continuous repeated outcomes and explicit seen/unseen-group prediction.

**[Grouped ordinal mixed-effects boosting →](grouped-ordinal-boosting.md)** extends grouped prediction to ordered outcomes with cumulative logits, ordered thresholds and group-aware validation.

### One-factor location–scale models

**[Gaussian hierarchical location–scale →](hierarchical-location-scale.md)** jointly models conditional mean and log residual scale with correlated group random intercepts.

**[Robust Student-t location–scale →](robust-hierarchical-location-scale.md)** replaces the conditional Gaussian distribution with a symmetric Student-t distribution while retaining the same mean/scale hierarchy.

**[Location random slope →](random-slope-location-scale.md)** adds one group-specific slope in the location equation.

**[Scale random slope →](random-scale-slope-location-scale.md)** adds one group-specific slope in the log-scale equation.

**[Joint random slopes →](joint-random-slopes-location-scale.md)** adds one location and one log-scale slope per group in a four-dimensional latent block.

### Crossed participant–item location–scale models

**[Crossed intercepts →](crossed-location-scale.md)** models participant and item/stimulus random intercepts in both location and scale equations with joint Laplace integration.

**[Crossed location slopes →](crossed-random-slopes-location-scale.md)** adds a location random slope for each crossed factor; PR #129 is exact-main certified at `d078e036…`.

**[Crossed scale slopes →](crossed-random-scale-slopes-location-scale.md)** adds a log-scale random slope for each crossed factor; the final PR #134 scientific state is certified at `33175e1d…`.

**[Crossed joint location + scale slopes →](crossed-joint-random-slopes-location-scale.md)** gives each participant and item a four-dimensional `(location intercept, location slope, log-scale intercept, log-scale slope)` block with an unrestricted positive-definite 4 × 4 covariance matrix. This is the current scientific baseline introduced by PR #136.

## Current certified scientific baseline

PR **#136** is formally exact-main certified at SHA **`e761a931b00e646d6f12be3475a68cd524803893`**, tree **`313ce0a801daf0ae7c4b9ce7a9e0af4610094994`**. The merge tree matches the qualified candidate tree, its sole parent is `0b7084352362d297dc05f127d4bcbc924cd24873`, and the GitHub signature is verified/valid.

Exact-main evidence:

- **14/14 workflow families green**;
- Tests #634: **12/12 platform/Python lanes green**;
- canonical Ubuntu 24.04.5 / CPython 3.12.14: **850/850 tests**, **15,171/15,171 statements**, Ruff/compile clean;
- frozen parity registry: **406/406 implemented, 0 pending**;
- Branch Coverage #412: **7,159/7,178 = 99.7353%** raw branches;
- **19** audited residual structural/caller-dominated arcs and **0 unexpected / 0 stale / 0 unaudited** debt;
- Interoperability #622: **14/14** real optional-backend lanes green;
- branch artifact **10389944415**, SHA-256 `9cc448013e4be26caf22de120089ba649c928aee0989728fdbf77e5409528abf`;
- formal checkpoint: PR #136 comment **5678239576**.

A later documentation-only/site descendant may describe this checkpoint but does **not** replace `e761a931…` as the scientific certification anchor. Stable `0.1.6` remains a distinct frozen release with its own release evidence.

## Scientific guardrails

These pages document statistical and computational methods, not automatic scientific interpretation. None of these methods by itself:

- identifies or corrects physiological/eye-tracking artifacts;
- establishes sensor validity or reliability;
- identifies causal effects; or
- infers emotion, stress, trust, preference, cognition, diagnosis or other latent states from recorded measurements.

Grouped boosting is predictive rather than causal. Random effects/slopes describe modelled heterogeneity rather than stable traits. Log-scale effects describe conditional residual heterogeneity rather than measurement quality by definition. Robust heavy tails are a distributional assumption, not an artifact score. Timebase and cardiac certificates bind declared provenance evidence; they do not prove hardware synchronization or sensor validity.