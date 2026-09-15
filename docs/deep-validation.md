# Deep validation and interoperability

<div class="gp-page-intro">
`gpbiometricspy` treats validation as a set of independent evidence layers rather than a single coverage percentage. Use this page to understand **what was checked, at which level, and what each check can legitimately support**.
</div>

<div class="gp-chip-row">
<span class="gp-chip">406 / 406 frozen exports</span>
<span class="gp-chip">12 / 12 platform lanes</span>
<span class="gp-chip">R ↔ Python golden fixtures</span>
<span class="gp-chip">14 / 14 backend lanes</span>
<span class="gp-chip">private real-data smoke</span>
<span class="gp-chip">strict docs + Pages</span>
</div>

## Evidence map

| Evidence layer | What it checks | What it does **not** prove |
|---|---|---|
| Frozen export audit | Exact implementation status of the 406-function `gpbiometrics 2.0.0` parity registry | Numerical equivalence for every possible input |
| Unit + regression suite | Deterministic functional behavior, guards, error paths and scientific invariants | External validity of a scientific claim |
| Statement coverage | Whether executable package statements are exercised by the suite | Correctness merely because a line ran |
| Raw + audited branch coverage | Decision-path execution plus explicit accounting for residual structural/caller-dominated arcs | That uncovered branches may be ignored without review |
| Deep R ↔ Python parity | Independent R and Python calculations on deterministic golden fixtures | Identity outside the declared fixtures and tolerances |
| Interoperability matrix | Real imports and smoke execution against floor/current optional backends | That upstream packages will never change behavior |
| Private real-data validation | Package operation on non-public recorded data without exposing those data | Population-level scientific generalisability |
| CodeQL + compile/lint checks | Static/security findings and source-level hygiene | Scientific validity or methodological appropriateness |
| Strict documentation build | Internal links, generated API/docs contracts, gallery references and site build integrity | That prose alone validates the underlying method |
| Reproducibility certificates | Deterministic binding of declared fit/evidence objects to recorded settings/results | Sensor validity, causality or truth of an interpretation |

<div class="gp-decision">
<strong>Read the layers together.</strong> Surface completeness, numerical parity, cross-platform execution, branch accounting, backend interoperability, real-data smoke testing, documentation integrity and scientific interpretation are different questions. No single green badge substitutes for the others.
</div>

## Current certified scientific checkpoint

PR **#136** is formally exact-main certified at merge SHA **`e761a931b00e646d6f12be3475a68cd524803893`**, tree **`313ce0a801daf0ae7c4b9ce7a9e0af4610094994`**, with sole parent `0b7084352362d297dc05f127d4bcbc924cd24873`. The GitHub merge signature is verified/valid and the merge tree exactly matches the qualified candidate tree.

The post-merge generation is **14/14 workflow families green**. Tests #634 is **12/12 platform/Python lanes green**; the canonical Ubuntu 24.04.5 / CPython 3.12.14 lane passes **850/850 tests**, **15,171/15,171 statements**, Ruff/compile clean, and **406/406 frozen exports with 0 pending**. Interoperability #622 is **14/14** across real optional backends at floor/current versions.

Branch Coverage #412 reports **7,159/7,178 = 99.7353% raw branch coverage**. The same **19** residual structural/caller-dominated arcs remain explicitly audited, with **0 unexpected**, **0 stale**, and **0 unaudited** branch debt; audited accounting is **7,178/7,178 = 100.0000%**. Evidence artifact **10389944415** has SHA-256 **`9cc448013e4be26caf22de120089ba649c928aee0989728fdbf77e5409528abf`**.

Formal certification checkpoint: PR #136 comment **5678239576**. A later documentation-only descendant may describe this state but does not replace `e761a931…` as the scientific certification anchor.

## R ↔ Python golden fixtures

`reference/golden/` contains deterministic numerical cases spanning EDA/GSR conversion, SCR normalization, HRV metrics, pupil smoothing, TTL changes, within-participant standardization and baseline correction. The `deep-parity` workflow runs the frozen R implementation and Python implementation independently and compares JSON results with explicit tolerances.

This is stronger than importing one implementation from the other or comparing two calls into the same code path: the R and Python calculations are produced independently before comparison.

## Optional backend CI

The `interoperability` workflow exercises both declared floor versions and current releases for:

- HeartPy;
- BioSPPy;
- pyHRV;
- NeuroKit2;
- MNE;
- pylsl; and
- pyxdf.

Smoke cases import and **execute** the relevant backend integration rather than testing only an absence/error path. The matrix is intended to detect changes in real dependency behavior while keeping those optional ecosystems outside the frozen 406-export contract.

## Branch accounting

The project reports raw branch coverage rather than hiding residual paths behind a rounded percentage. Any branch intentionally retained in the audited structural-debt ledger must correspond to a reviewed structural or caller-dominated path. The audit separately checks for:

<div class="gp-metric-grid">
<div class="gp-metric-card"><strong>Unexpected</strong><span>currently missing branches not present in the reviewed ledger</span></div>
<div class="gp-metric-card"><strong>Stale</strong><span>ledger entries that no longer correspond to a missing branch</span></div>
<div class="gp-metric-card"><strong>Unaudited</strong><span>missing branch debt without an explicit reviewed classification</span></div>
<div class="gp-metric-card"><strong>Denominator</strong><span>a frozen contract that must advance when legitimate new branch paths are added</span></div>
</div>

A denominator change is therefore not silently absorbed. New executable decision paths must either be covered or explicitly reconciled with the structural-debt contract.

## Private real-data validation

Synthetic data are essential for deterministic testing, but they cannot reproduce every recorded-data irregularity. A separate private workflow therefore smoke-tests the package against non-public recordings while keeping those files outside the repository and public artifacts.

Passing this layer means the tested real-data workflow executed under the declared checks. It does **not** transform one private dataset into evidence of external validity, sensor validity or universal robustness.

## Documentation as executable evidence

Documentation CI is intentionally more than Markdown rendering. The build generates API pages and scientific gallery figures from the checked-out package, validates documentation contracts and references, runs `mkdocs build --strict`, and deploys Pages only from `main`.

Exact-main Docs #397 completed successfully and deployed the certified scientific SHA to the Pages branch before this separate site-redesign lineage was prepared. That keeps scientific certification and later presentation changes distinguishable.

<div class="gp-actions">
<a class="md-button md-button--primary" href="../parity/">Inspect the parity contract</a>
<a class="md-button" href="../real-data-validation/">Private real-data validation</a>
<a class="md-button" href="../integrations/">Integration matrix</a>
<a class="md-button" href="../plot-gallery/">Generated visual evidence</a>
</div>

## Scientific boundary

Green validation evidence supports claims about the **software checks that were actually run**. It does not by itself establish causal effects, construct validity, clinical validity, emotional state, stress, trust, preference, cognition, diagnosis, sensor reliability, hardware synchronization beyond available timing evidence, or generalisability beyond the study design.

For a paper or supplement, report the measurement evidence, preprocessing decisions, timing assumptions, model specification and scientific limitations alongside software-version and validation evidence—not instead of them.