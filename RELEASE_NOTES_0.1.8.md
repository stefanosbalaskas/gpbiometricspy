# gpbiometricspy 0.1.8 — PPG measurement equity and STEP evidence

Stable-freeze candidate prepared **2026-10-04**.

`gpbiometricspy 0.1.8` preserves the frozen **406/406** `gpbiometrics 2.0.0` semantic contract with **0 pending exports** while promoting the post-0.1.7 PPG pigmentation / measurement-equity programme into the stable release scope.

## Qualified source

The release-preparation baseline is exact `main` commit:

```text
a75eb1d73791213e6e830ff94975f632455632e2
```

On that exact source:

- **12/12** OS × Python 3.11–3.14 test lanes passed;
- **874/874** tests passed;
- **15,612/15,612 statements = 100.00%**;
- raw branch coverage is **7,315/7,334 = 99.7409%**;
- exactly **19** residual structural arcs are reviewed;
- **0 unexpected / 0 stale / 0 unaudited** branch debt remains;
- audited branch accounting is **7,334/7,334 = 100.0000%**;
- docs/Pages, CodeQL, deep R↔Python parity, optional-backend interoperability, private real-data validation and release-handoff safety are green.

The stable-freeze pull request and the merged stable source must still pass their own protected exact-head/exact-main gates before publication.

## PPG pigmentation / measurement-equity audit

The release adds a Python-native PPG accountability surface outside the frozen R export registry:

- `compute_skin_ita()`;
- `validate_skin_pigmentation_metadata()`;
- `summarize_ppg_quality_by_pigmentation()`;
- `compare_ppg_reference_by_pigmentation()`;
- `ppg_pigmentation_audit()`.

The workflow deliberately separates:

1. pigmentation-measurement provenance;
2. raw PPG signal quality;
3. retention / paired availability;
4. paired reference agreement.

Objective CIELAB/ITA-style measurements can support continuous descriptive association models. Subjective scales such as Fitzpatrick remain subjective categorical provenance and are not converted into objective pigmentation, melanin, race, ethnicity or ITA. Race/ethnicity are not accepted as substitutes for measured pigmentation.

The package does not apply a universal pigmentation correction, does not automatically exclude observations based on pigmentation, and does not label devices “fair” or “unfair”.

## Deterministic evidence

A deterministic synthetic example demonstrates the core analytical distinction:

```text
amplitude ≠ quality ≠ retention ≠ accuracy
```

The generated figures and derived summaries are regression-tested and documented with the corresponding PPG, SQI, retention, agreement and participant-cluster-bootstrap equations.

## Authorized STEP evidence

BigIdeasLab_STEP v1.0 was executed locally under the applicable PhysioNet DUA against exact scientific source:

```text
dc2b539154f65061a90d360f01503108ad1fd39f
```

Recorded aggregate evidence:

- source DOI: `10.13026/cqfy-d860`;
- 53 participants;
- 1,431,570 long-format wearable rows;
- 1,328,850 rows with ECG reference available;
- 361,675 paired wearable/ECG measurements;
- six wearable devices;
- Rest, Activity, Breathe and Type strata plus an observed unlabeled/NA stratum;
- 1,000 participant-cluster bootstrap replicates, seed `20261003`;
- derived-only evidence bundle SHA256: `65EF1DE84CF711F9E6753DB771E3E2386FD6926A104E0D4DC1618EE88E8744B1`.

Restricted participant-level rows were not committed or redistributed.

### STEP interpretation boundary

Fitzpatrick phototype 1–6 is treated as a **subjective categorical** measure. Continuous objective-pigmentation association models are therefore intentionally not promoted from STEP.

STEP row-level `retention_rate` is interpreted as **paired availability/reporting density** on the source grid. Because device reporting cadence differs materially, this quantity must not be relabelled as generic device missingness, dropout or fairness.

The unlabeled/NA activity stratum remains explicitly unlabeled. No physiological condition is inferred from it.

Agreement results are observational and device/activity-specific; they do not establish causal optical mechanisms or universal device fairness.

## ENCoDE and SpO₂ boundaries

The ENCoDE adapter, schema contract and synthetic fixture remain available as future evidence infrastructure, but real ENCoDE execution is **deferred** and is not claimed in 0.1.8.

This release is a PPG/heart-rate and measurement-accountability tranche. It is **not clinical SpO₂ validation** and does not make pulse-oximeter diagnostic-performance claims.

## Citation and archival boundary

- software concept DOI: `10.5281/zenodo.22150872`;
- frozen R semantic-reference DOI: `10.5281/zenodo.21434608`;
- no 0.1.7 or 0.1.8 version DOI is invented before genuine independent Zenodo verification.

`CITATION.cff`, `.zenodo.json`, package/runtime identity and generated documentation metadata are synchronized to `0.1.8` / `2026-10-04` for the stable-freeze candidate.

## Publication boundary

This release-note file does **not** itself create a release. Immutable `v0.1.8`, GitHub Release assets and PyPI Trusted Publishing are allowed only after the exact stable candidate is qualified, merged with a pinned head, and the resulting exact `main` commit passes every protected release gate.