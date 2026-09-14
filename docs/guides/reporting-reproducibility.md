# Reporting and reproducibility

<div class="gp-page-intro">
A reproducible analysis is more than code that runs once. This guide focuses on the evidence that should survive the analysis: input identity, QC, timing, preprocessing, modelling assumptions, software versions, generated figures, and scientific boundaries.
</div>

## The minimum reporting bundle

<div class="gp-metric-grid">
<div class="gp-metric-card"><strong>Input</strong><span>Source files, schema, units, participants/sessions, acquisition context.</span></div>
<div class="gp-metric-card"><strong>QC</strong><span>Missingness, validity, dropouts, timing, exclusions, review decisions.</span></div>
<div class="gp-metric-card"><strong>Methods</strong><span>Parameters, thresholds, windows, model formulae, prediction semantics.</span></div>
<div class="gp-metric-card"><strong>Software</strong><span>Package version, Python version, optional backend versions, certificates.</span></div>
</div>

## Capture software identity early

```python
import platform
import gpbiometricspy as gp

software = {
    "gpbiometricspy": gp.__version__,
    "python": platform.python_version(),
}
```

If an optional backend contributes to the scientific result, record its version too. The public interoperability matrix tests supported floor/current combinations, but a manuscript should still state what the study actually used.

## Retain QC as data

Do not reduce QC to “data were cleaned.” Keep the tables or objects that support each decision.

```python
activity = gp.audit_gazepoint_signal_activity(
    dat,
    signal_cols=["GSR_US", "HR", "IBI", "LPMM"],
    group_cols=["participant_id"],
)

resets = gp.audit_gazepoint_time_resets(
    dat,
    time_col="TIME",
    group_cols=["participant_id"],
)
```

![Missingness overview](../assets/generated/missingness.png)

The exact QC functions depend on modality, but the reporting principle is stable: retain the evidence that justified inclusion, exclusion, interpolation, or model readiness.

## Report transformations in scientific order

A methods section is easier to audit when it follows the order in which information was transformed:

1. acquisition/export and source identity;
2. schema standardisation;
3. timebase and signal QC;
4. preprocessing and artifact rules;
5. event/AOI alignment;
6. feature construction;
7. statistical or predictive modelling;
8. sensitivity checks;
9. software and reproducibility information.

This order prevents downstream model details from obscuring earlier measurement assumptions.

## What to report for modelling

For grouped or hierarchical models, state:

- outcome and predictor definitions;
- grouping factors and whether levels are crossed or nested;
- fixed effects;
- random-effect structure;
- distributional family;
- estimation/integration strategy where relevant;
- how unseen groups/items are handled;
- validation split unit;
- optimization/convergence diagnostics;
- uncertainty or the explicit absence of inferential intervals;
- sensitivity or known-truth validation used to bound claims.

For the Python-native method families, use the dedicated [Methods](../methods/index.md) pages rather than inferring semantics from class or function names.

## Figures are evidence, not decoration

Keep the figures used for decisions, including failed or borderline checks when they affected the analysis. The documentation gallery is generated from package functions and provides examples of the kinds of diagnostics worth retaining.

<div class="gp-visual-grid">
<a class="gp-visual-card" href="../plot-gallery/#eda-and-scr">
<img src="../assets/generated/eda-decomposition.png" alt="EDA decomposition showing observed tonic and phasic components">
<div class="gp-visual-card-body"><strong>Signal processing evidence</strong><span>Show what a transformation did rather than only reporting its name.</span></div>
</a>
<a class="gp-visual-card" href="../plot-gallery/#ppg-and-hrv">
<img src="../assets/generated/ppg-peak-detection.png" alt="PPG waveform with accepted pulse peaks">
<div class="gp-visual-card-body"><strong>Event-detection evidence</strong><span>Retain accepted/rejected event logic when derived intervals feed later analyses.</span></div>
</a>
</div>

## Reproducibility checklist

- [ ] Raw inputs are immutable or checksummed.
- [ ] Schema/renaming decisions are recorded.
- [ ] Sampling and timebase evidence is retained.
- [ ] QC outputs and warnings are saved.
- [ ] Exclusions have machine-readable reasons.
- [ ] Preprocessing settings are explicit.
- [ ] Random seeds are fixed where stochastic procedures are used.
- [ ] Optional backend versions are recorded.
- [ ] Figures used for QC are generated from code.
- [ ] Model specification and prediction target are explicit.
- [ ] Scientific interpretation is narrower than or equal to what the design supports.

## Where to go next

- [Reporting and reproducibility workflow](../articles/reporting-reproducibility-workflow.md) — frozen R-companion workflow.
- [Private real-data smoke testing](../articles/private-real-data-smoke-testing.md) — validate private data without committing it.
- [Citation and archival](../citation.md) — package citation and software archive information.
- [Validation & trust](../parity.md) — parity and certification evidence.
